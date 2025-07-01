"""
图像哈希器模块

实现dHash (difference hash) 算法的Python版本。
使用Pillow进行图像处理，与原始TypeScript实现保持兼容性。
"""

import io
from typing import Optional, Union, Tuple, Dict, List, Any
try:
    from PIL import Image  # type: ignore
except ImportError:
    raise ImportError("PIL (Pillow) is required. Install with: pip install Pillow")

import requests

from ..utils.logger import get_logger

logger = get_logger(__name__)


class ImageHasher:
    """图像哈希器类 - Python实现的dHash算法"""
    
    def __init__(self, hash_size: int = 8):
        """
        初始化图像哈希器
        
        Args:
            hash_size: 哈希大小，默认为8 (生成64位哈希)
        """
        self.hash_size = hash_size
    
    def hash_image_data(self, image_data: bytes) -> str:
        """
        从图像字节数据生成dHash
        
        Args:
            image_data: 图像字节数据
            
        Returns:
            str: 64位二进制哈希字符串
        """
        try:
            # 从字节数据加载图像
            image = Image.open(io.BytesIO(image_data))
            
            # 预处理图像
            grayscale_pixels = self._preprocess_image(image)
            
            # 计算dHash
            hash_string = self._calculate_dhash(grayscale_pixels)
            
            logger.debug(f"成功生成图像哈希: {hash_string[:16]}...")
            return hash_string
            
        except Exception as e:
            logger.error(f"生成图像哈希失败: {e}")
            return ""
    
    def hash_image_from_url(self, image_url: str, 
                           headers: Optional[Dict[str, str]] = None,
                           timeout: int = 30) -> str:
        """
        从URL下载图像并生成哈希
        
        Args:
            image_url: 图像URL
            headers: 请求头
            timeout: 超时时间
            
        Returns:
            str: 64位二进制哈希字符串
        """
        try:
            logger.debug(f"从URL下载图像: {image_url}")
            
            # 下载图像
            response = requests.get(
                image_url, 
                headers=headers or {}, 
                timeout=timeout,
                stream=True
            )
            response.raise_for_status()
            
            # 生成哈希
            hash_string = self.hash_image_data(response.content)
            
            if hash_string:
                logger.info(f"成功从URL生成哈希: {image_url}")
            else:
                logger.error(f"从URL生成哈希失败: {image_url}")
            
            return hash_string
            
        except requests.RequestException as e:
            logger.error(f"下载图像失败 {image_url}: {e}")
            return ""
        except Exception as e:
            logger.error(f"从URL生成哈希异常 {image_url}: {e}")
            return ""
    
    def hash_image_file(self, file_path: str) -> str:
        """
        从本地文件生成哈希
        
        Args:
            file_path: 图像文件路径
            
        Returns:
            str: 64位二进制哈希字符串
        """
        try:
            logger.debug(f"从文件生成哈希: {file_path}")
            
            with open(file_path, 'rb') as f:
                image_data = f.read()
            
            hash_string = self.hash_image_data(image_data)
            
            if hash_string:
                logger.info(f"成功从文件生成哈希: {file_path}")
            else:
                logger.error(f"从文件生成哈希失败: {file_path}")
            
            return hash_string
            
        except Exception as e:
            logger.error(f"从文件生成哈希异常 {file_path}: {e}")
            return ""
    
    def _preprocess_image(self, image: Any) -> List[int]:  # type: ignore
        """
        预处理图像：缩放并转换为灰度
        
        Args:
            image: PIL图像对象
            
        Returns:
            List[int]: 灰度像素值列表
        """
        try:
            # 计算目标尺寸 (width = hash_size + 1, height = hash_size)
            scaled_width = self.hash_size + 1
            scaled_height = self.hash_size
            
            # 缩放图像
            resized_image = image.resize(
                (scaled_width, scaled_height), 
                Image.Resampling.LANCZOS
            )
            
            # 转换为灰度
            grayscale_image = resized_image.convert('L')
            
            # 获取像素值
            pixels = list(grayscale_image.getdata())
            
            logger.debug(f"图像预处理完成: {scaled_width}x{scaled_height}, {len(pixels)} 像素")
            return pixels
            
        except Exception as e:
            logger.error(f"图像预处理失败: {e}")
            return []
    
    def _calculate_dhash(self, pixels: List[int]) -> str:
        """
        计算dHash (difference hash)
        
        Args:
            pixels: 灰度像素值列表
            
        Returns:
            str: 二进制哈希字符串
        """
        try:
            hash_bits = []
            width = self.hash_size + 1
            
            # 遍历每一行
            for y in range(self.hash_size):
                # 遍历每一列 (除了最后一列)
                for x in range(self.hash_size):
                    # 获取相邻像素
                    left_pixel = pixels[y * width + x]
                    right_pixel = pixels[y * width + x + 1]
                    
                    # 比较相邻像素，左边小于右边则为1，否则为0
                    bit = "1" if left_pixel < right_pixel else "0"
                    hash_bits.append(bit)
            
            # 连接所有位形成哈希字符串
            hash_string = "".join(hash_bits)
            
            logger.debug(f"dHash计算完成: {len(hash_string)} 位")
            return hash_string
            
        except Exception as e:
            logger.error(f"dHash计算失败: {e}")
            return ""
    
    @staticmethod
    def hamming_distance(hash1: str, hash2: str) -> int:
        """
        计算两个二进制哈希字符串的汉明距离
        
        Args:
            hash1: 第一个哈希字符串
            hash2: 第二个哈希字符串
            
        Returns:
            int: 汉明距离
        """
        try:
            if len(hash1) != len(hash2):
                raise ValueError(f"哈希长度不匹配: {len(hash1)} vs {len(hash2)}")
            
            # 使用异或运算计算差异
            diff_count = 0
            for bit1, bit2 in zip(hash1, hash2):
                if bit1 != bit2:
                    diff_count += 1
            
            return diff_count
            
        except Exception as e:
            logger.error(f"汉明距离计算失败: {e}")
            return -1
    
    @staticmethod
    def similarity_percentage(hash1: str, hash2: str) -> float:
        """
        计算两个哈希的相似度百分比
        
        Args:
            hash1: 第一个哈希字符串
            hash2: 第二个哈希字符串
            
        Returns:
            float: 相似度百分比 (0-100)
        """
        try:
            if len(hash1) != len(hash2):
                return 0.0
            
            hamming_dist = ImageHasher.hamming_distance(hash1, hash2)
            if hamming_dist < 0:
                return 0.0
            
            similarity = (1 - hamming_dist / len(hash1)) * 100
            return max(0.0, similarity)
            
        except Exception as e:
            logger.error(f"相似度计算失败: {e}")
            return 0.0
    
    def validate_hash_format(self, hash_string: str) -> bool:
        """
        验证哈希格式
        
        Args:
            hash_string: 哈希字符串
            
        Returns:
            bool: 格式正确返回True
        """
        expected_length = self.hash_size * self.hash_size
        
        # 检查长度
        if len(hash_string) != expected_length:
            logger.warning(f"哈希长度错误: 期望 {expected_length}, 实际 {len(hash_string)}")
            return False
        
        # 检查字符
        if not all(c in '01' for c in hash_string):
            logger.warning(f"哈希包含非二进制字符: {hash_string}")
            return False
        
        return True
    
    def get_hash_info(self, hash_string: str) -> dict:
        """
        获取哈希信息
        
        Args:
            hash_string: 哈希字符串
            
        Returns:
            dict: 哈希信息
        """
        info = {
            "hash": hash_string,
            "length": len(hash_string),
            "expected_length": self.hash_size * self.hash_size,
            "is_valid": self.validate_hash_format(hash_string),
            "hash_size": self.hash_size,
            "ones_count": hash_string.count('1'),
            "zeros_count": hash_string.count('0')
        }
        
        if info["length"] > 0:
            info["ones_percentage"] = (info["ones_count"] / info["length"]) * 100
            info["zeros_percentage"] = (info["zeros_count"] / info["length"]) * 100
        else:
            info["ones_percentage"] = 0.0
            info["zeros_percentage"] = 0.0
        
        return info
    
    def batch_hash_from_urls(self, url_list: List[str], 
                           headers: Optional[Dict[str, str]] = None,
                           timeout: int = 30) -> Dict[str, Optional[str]]:
        """
        批量从URL生成哈希
        
        Args:
            url_list: URL列表
            headers: 请求头
            timeout: 超时时间
            
        Returns:
            dict: URL到哈希的映射
        """
        logger.info(f"开始批量生成哈希: {len(url_list)} 个URL")
        
        results = {}
        success_count = 0
        
        for i, url in enumerate(url_list, 1):
            try:
                logger.debug(f"处理第 {i}/{len(url_list)} 个URL: {url}")
                
                hash_string = self.hash_image_from_url(url, headers, timeout)
                
                if hash_string:
                    results[url] = hash_string
                    success_count += 1
                else:
                    results[url] = None
                    
            except Exception as e:
                logger.error(f"批量处理URL异常 {url}: {e}")
                results[url] = None
        
        logger.info(f"批量哈希生成完成: 成功 {success_count}/{len(url_list)}")
        return results
    
    def compare_with_database(self, new_hash: str, 
                            hash_database: dict,
                            threshold: int = 5) -> list:
        """
        与哈希数据库比较找出相似图像
        
        Args:
            new_hash: 新的哈希值
            hash_database: 哈希数据库 {hash: metadata}
            threshold: 相似度阈值 (汉明距离)
            
        Returns:
            list: 相似图像列表
        """
        similar_images = []
        
        try:
            for stored_hash, metadata in hash_database.items():
                distance = self.hamming_distance(new_hash, stored_hash)
                
                if 0 <= distance <= threshold:
                    similarity = self.similarity_percentage(new_hash, stored_hash)
                    similar_images.append({
                        "hash": stored_hash,
                        "metadata": metadata,
                        "hamming_distance": distance,
                        "similarity_percentage": similarity
                    })
            
            # 按相似度排序
            similar_images.sort(key=lambda x: x["hamming_distance"])
            
            logger.debug(f"找到 {len(similar_images)} 个相似图像")
            
        except Exception as e:
            logger.error(f"哈希比较异常: {e}")
        
        return similar_images


def hash_image_data(image_data: bytes, hash_size: int = 8) -> str:
    """
    生成图像哈希（便捷函数）
    
    Args:
        image_data: 图像字节数据
        hash_size: 哈希大小
        
    Returns:
        str: 二进制哈希字符串
    """
    hasher = ImageHasher(hash_size)
    return hasher.hash_image_data(image_data)


def hash_image_from_url(image_url: str, 
                       headers: Optional[dict] = None,
                       timeout: int = 30,
                       hash_size: int = 8) -> str:
    """
    从URL生成图像哈希（便捷函数）
    
    Args:
        image_url: 图像URL
        headers: 请求头
        timeout: 超时时间
        hash_size: 哈希大小
        
    Returns:
        str: 二进制哈希字符串
    """
    hasher = ImageHasher(hash_size)
    return hasher.hash_image_from_url(image_url, headers, timeout)


def hamming_distance(hash1: str, hash2: str) -> int:
    """
    计算汉明距离（便捷函数）
    
    Args:
        hash1: 第一个哈希
        hash2: 第二个哈希
        
    Returns:
        int: 汉明距离
    """
    return ImageHasher.hamming_distance(hash1, hash2)
