"""
Change tracking system for monitoring pipeline operations and generating commit messages.

This module provides centralized tracking of changes made during the pipeline execution,
including duplicate removal, hash generation, file processing, and minification operations.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Any
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ChangeStatistics:
    """Statistics for a specific type of change."""
    count: int = 0
    files_affected: Set[str] = field(default_factory=set)
    details: List[str] = field(default_factory=list)


@dataclass
class DomainChanges:
    """Changes made to a specific domain."""
    domain: str
    duplicates_removed: ChangeStatistics = field(default_factory=ChangeStatistics)
    hashes_created: ChangeStatistics = field(default_factory=ChangeStatistics)
    files_sorted: ChangeStatistics = field(default_factory=ChangeStatistics)
    files_minified: ChangeStatistics = field(default_factory=ChangeStatistics)
    image_links: List[str] = field(default_factory=list)


class ChangeTracker:
    """Tracks changes across the entire pipeline execution."""
    
    def __init__(self):
        """Initialize the change tracker."""
        self.domains: Dict[str, DomainChanges] = {}
        self.start_time = datetime.now()
        self.validation_errors_fixed = 0
        self.total_files_processed = 0
        
    def add_domain(self, domain: str) -> DomainChanges:
        """
        Add or get a domain for tracking changes.
        
        Args:
            domain: Domain name (e.g., 'www.xiguashuwu.com')
            
        Returns:
            DomainChanges object for the domain
        """
        if domain not in self.domains:
            self.domains[domain] = DomainChanges(domain=domain)
        return self.domains[domain]
    
    def track_duplicates_removed(self, domain: str, count: int, filename: str, removed_items: List[str]):
        """
        Track duplicate entries removed from filename mappings.
        
        Args:
            domain: Domain name
            count: Number of duplicates removed
            filename: File where duplicates were removed
            removed_items: List of removed items for details
        """
        domain_changes = self.add_domain(domain)
        domain_changes.duplicates_removed.count += count
        domain_changes.duplicates_removed.files_affected.add(filename)
        domain_changes.duplicates_removed.details.extend([f"移除重复项: {item}" for item in removed_items])
        
        logger.info(f"跟踪记录: {domain} 移除了 {count} 个重复项")
    
    def track_hashes_created(self, domain: str, hash_mapping: Dict[str, str], filename: str):
        """
        Track new hashes created for characters.
        
        Args:
            domain: Domain name
            hash_mapping: Dictionary of new hashes created (hash -> character)
            filename: Hash mapping file that was updated
        """
        domain_changes = self.add_domain(domain)
        count = len(hash_mapping)
        domain_changes.hashes_created.count += count
        domain_changes.hashes_created.files_affected.add(filename)
        
        # Generate image links for each new hash
        for hash_value, character in hash_mapping.items():
            # Create a reference to the image file
            image_link = f"字符 '{character}' 的图像哈希: {hash_value[:16]}..."
            domain_changes.image_links.append(image_link)
            domain_changes.hashes_created.details.append(f"新建哈希: {character} -> {hash_value[:16]}...")
        
        logger.info(f"跟踪记录: {domain} 创建了 {count} 个新哈希")
    
    def track_files_sorted(self, domain: str, filename: str, entries_count: int):
        """
        Track file sorting operations.
        
        Args:
            domain: Domain name
            filename: File that was sorted
            entries_count: Number of entries sorted
        """
        domain_changes = self.add_domain(domain)
        domain_changes.files_sorted.count += entries_count
        domain_changes.files_sorted.files_affected.add(filename)
        domain_changes.files_sorted.details.append(f"排序文件: {filename} ({entries_count} 条目)")
        
        logger.debug(f"跟踪记录: {domain} 排序了 {filename}")
    
    def track_files_minified(self, domain: str, source_file: str, target_file: str, size_reduction: int):
        """
        Track file minification operations.
        
        Args:
            domain: Domain name
            source_file: Source file path
            target_file: Minified file path
            size_reduction: Size reduction in bytes
        """
        domain_changes = self.add_domain(domain)
        domain_changes.files_minified.count += 1
        domain_changes.files_minified.files_affected.add(target_file)
        domain_changes.files_minified.details.append(f"压缩文件: {target_file} (减少 {size_reduction} 字节)")
        
        logger.debug(f"跟踪记录: {domain} 压缩了 {target_file}")
    
    def get_total_changes(self) -> Dict[str, int]:
        """
        Get total changes across all domains.
        
        Returns:
            Dictionary with total change counts
        """
        totals = {
            'duplicates_removed': 0,
            'hashes_created': 0,
            'files_sorted': 0,
            'files_minified': 0,
            'domains_processed': len(self.domains)
        }
        
        for domain_changes in self.domains.values():
            totals['duplicates_removed'] += domain_changes.duplicates_removed.count
            totals['hashes_created'] += domain_changes.hashes_created.count
            totals['files_sorted'] += domain_changes.files_sorted.count
            totals['files_minified'] += domain_changes.files_minified.count
        
        return totals
    
    def has_significant_changes(self) -> bool:
        """
        Check if there are significant changes worth committing.
        
        Returns:
            True if there are significant changes
        """
        totals = self.get_total_changes()
        return (totals['duplicates_removed'] > 0 or 
                totals['hashes_created'] > 0 or 
                totals['files_sorted'] > 0 or 
                totals['files_minified'] > 0)
    
    def generate_commit_title(self) -> str:
        """
        Generate a short, descriptive commit title.
        
        Returns:
            Commit title string
        """
        totals = self.get_total_changes()
        
        if not self.has_significant_changes():
            return "🔧 维护: 运行流水线检查"
        
        parts = []
        if totals['hashes_created'] > 0:
            parts.append(f"新增{totals['hashes_created']}个哈希")
        if totals['duplicates_removed'] > 0:
            parts.append(f"清理{totals['duplicates_removed']}个重复项")
        if totals['files_minified'] > 0:
            parts.append(f"压缩{totals['files_minified']}个文件")
        
        if len(parts) == 0:
            return "🔄 更新: 处理映射文件"
        
        title = "🤖 " + "、".join(parts)
        if len(title) > 50:  # Keep title short
            title = f"🤖 处理{totals['domains_processed']}个域的映射文件"
        
        return title
    
    def generate_commit_description(self) -> str:
        """
        Generate a detailed commit description.
        
        Returns:
            Commit description string
        """
        if not self.has_significant_changes():
            return "运行自动化流水线检查，未发现需要更改的内容。"
        
        lines = ["自动化流水线处理结果:", ""]
        
        totals = self.get_total_changes()
        
        # Summary section
        lines.append("## 处理摘要")
        lines.append(f"- 处理域数量: {totals['domains_processed']}")
        if totals['duplicates_removed'] > 0:
            lines.append(f"- 移除重复项: {totals['duplicates_removed']} 个")
        if totals['hashes_created'] > 0:
            lines.append(f"- 创建新哈希: {totals['hashes_created']} 个")
        if totals['files_sorted'] > 0:
            lines.append(f"- 排序文件: {totals['files_sorted']} 个条目")
        if totals['files_minified'] > 0:
            lines.append(f"- 压缩文件: {totals['files_minified']} 个")
        
        lines.append("")
        
        # Domain-specific details
        for domain, changes in self.domains.items():
            if self._has_domain_changes(changes):
                lines.append(f"## {domain}")
                
                if changes.duplicates_removed.count > 0:
                    lines.append(f"### 移除重复项 ({changes.duplicates_removed.count})")
                    for detail in changes.duplicates_removed.details[:5]:  # Limit details
                        lines.append(f"- {detail}")
                    if len(changes.duplicates_removed.details) > 5:
                        lines.append(f"- ... 还有 {len(changes.duplicates_removed.details) - 5} 项")
                    lines.append("")
                
                if changes.hashes_created.count > 0:
                    lines.append(f"### 新建哈希 ({changes.hashes_created.count})")
                    for detail in changes.hashes_created.details[:5]:  # Limit details
                        lines.append(f"- {detail}")
                    if len(changes.hashes_created.details) > 5:
                        lines.append(f"- ... 还有 {len(changes.hashes_created.details) - 5} 项")
                    lines.append("")
                
                if changes.image_links:
                    lines.append("### 图像文件引用")
                    for link in changes.image_links[:3]:  # Limit links
                        lines.append(f"- {link}")
                    if len(changes.image_links) > 3:
                        lines.append(f"- ... 还有 {len(changes.image_links) - 3} 个图像哈希")
                    lines.append("")
        
        # Processing time
        duration = datetime.now() - self.start_time
        lines.append(f"处理时间: {duration.total_seconds():.1f} 秒")
        
        return "\n".join(lines)
    
    def _has_domain_changes(self, changes: DomainChanges) -> bool:
        """Check if a domain has any significant changes."""
        return (changes.duplicates_removed.count > 0 or 
                changes.hashes_created.count > 0 or 
                changes.files_sorted.count > 0 or 
                changes.files_minified.count > 0)
    
    def export_to_json(self, output_path: Path):
        """
        Export change tracking data to JSON file for workflow consumption.
        
        Args:
            output_path: Path to output JSON file
        """
        data: Dict[str, Any] = {
            'timestamp': datetime.now().isoformat(),
            'has_changes': self.has_significant_changes(),
            'commit_title': self.generate_commit_title(),
            'commit_description': self.generate_commit_description(),
            'totals': self.get_total_changes(),
            'domains': {}
        }
        
        for domain, changes in self.domains.items():
            data['domains'][domain] = {
                'duplicates_removed': changes.duplicates_removed.count,
                'hashes_created': changes.hashes_created.count,
                'files_sorted': changes.files_sorted.count,
                'files_minified': changes.files_minified.count,
                'image_links': changes.image_links
            }
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"变更跟踪数据已导出到: {output_path}")
        except Exception as e:
            logger.error(f"导出变更跟踪数据失败: {e}")
