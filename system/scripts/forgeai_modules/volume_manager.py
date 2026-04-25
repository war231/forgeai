"""
多卷大纲管理模块
支持卷级管理、统计、进度跟踪
"""
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime


class VolumeInfo:
    """卷信息"""
    def __init__(
        self,
        volume_id: int,
        name: str,
        chapter_count: int = 0,
        word_count: int = 0,
        status: str = "draft",  # draft/writing/completed
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
    ):
        self.volume_id = volume_id
        self.name = name
        self.chapter_count = chapter_count
        self.word_count = word_count
        self.status = status
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "volume_id": self.volume_id,
            "name": self.name,
            "chapter_count": self.chapter_count,
            "word_count": self.word_count,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class VolumeManager:
    """多卷大纲管理器"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.forgeai_dir = project_root / ".forgeai"
        self.state_file = self.forgeai_dir / "state.json"
        self.outline_dir = project_root / "3-大纲"
        self.content_dir = project_root / "4-正文"
        
    def _load_state(self) -> Dict[str, Any]:
        """加载状态文件"""
        if not self.state_file.exists():
            return {}
        return json.loads(self.state_file.read_text(encoding="utf-8"))
    
    def _save_state(self, state: Dict[str, Any]) -> None:
        """保存状态文件"""
        state["project"]["updated_at"] = datetime.now().isoformat()
        self.state_file.write_text(
            json.dumps(state, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    
    def _scan_volumes(self) -> Dict[int, VolumeInfo]:
        """扫描所有卷"""
        volumes = {}
        
        # 扫描大纲目录
        for volume_dir in self.outline_dir.iterdir():
            if volume_dir.is_dir() and volume_dir.name.startswith("第") and volume_dir.name.endswith("卷"):
                # 解析卷号
                try:
                    volume_name = volume_dir.name
                    volume_id = int(volume_name.replace("第", "").replace("卷", ""))
                except ValueError:
                    continue
                
                # 统计章节
                chapter_files = list(volume_dir.glob("第*章.md"))
                chapter_count = len(chapter_files)
                
                # 统计字数（大纲字数）
                word_count = 0
                for chapter_file in chapter_files:
                    content = chapter_file.read_text(encoding="utf-8")
                    word_count += len(content.replace(" ", "").replace("\n", ""))
                
                # 确定状态
                status = "draft"
                if chapter_count > 0:
                    # 检查是否有对应的正文
                    content_volume_dir = self.content_dir / volume_name
                    if content_volume_dir.exists():
                        written_chapters = len(list(content_volume_dir.glob("第*章*.md")))
                        if written_chapters == chapter_count:
                            status = "completed"
                        elif written_chapters > 0:
                            status = "writing"
                
                volumes[volume_id] = VolumeInfo(
                    volume_id=volume_id,
                    name=volume_name,
                    chapter_count=chapter_count,
                    word_count=word_count,
                    status=status,
                )
        
        return volumes
    
    def list_volumes(self) -> Dict[str, Any]:
        """列出所有卷"""
        volumes = self._scan_volumes()
        state = self._load_state()
        
        result = {
            "total_volumes": len(volumes),
            "current_volume": state.get("progress", {}).get("current_volume", 1),
            "volumes": [],
        }
        
        for volume_id in sorted(volumes.keys()):
            volume = volumes[volume_id]
            result["volumes"].append(volume.to_dict())
        
        return result
    
    def add_volume(self, name: Optional[str] = None) -> Dict[str, Any]:
        """添加新卷"""
        # 扫描现有卷
        volumes = self._scan_volumes()
        next_volume_id = max(volumes.keys()) + 1 if volumes else 1
        
        # 创建卷名
        volume_name = name or f"第{next_volume_id}卷"
        
        # 创建目录
        volume_outline_dir = self.outline_dir / volume_name
        volume_outline_dir.mkdir(exist_ok=True)
        
        # 更新状态
        state = self._load_state()
        state["progress"]["total_volumes"] = next_volume_id
        self._save_state(state)
        
        return {
            "status": "ok",
            "volume_id": next_volume_id,
            "name": volume_name,
            "message": f"已创建新卷：{volume_name}",
        }
    
    def get_volume_status(self, volume_id: int) -> Optional[Dict[str, Any]]:
        """获取卷状态"""
        volumes = self._scan_volumes()
        
        if volume_id not in volumes:
            return None
        
        volume = volumes[volume_id]
        state = self._load_state()
        
        # 获取详细章节列表
        volume_dir = self.outline_dir / volume.name
        chapters = []
        
        for chapter_file in sorted(volume_dir.glob("第*章.md")):
            chapter_name = chapter_file.stem
            chapter_num = int(chapter_name.replace("第", "").replace("章", ""))
            
            # 检查正文状态
            content_file = self.content_dir / volume.name / f"{chapter_name}*.md"
            content_files = list(self.content_dir.glob(f"{volume.name}/{chapter_name}*.md"))
            written = len(content_files) > 0
            
            # 统计字数
            outline_words = len(chapter_file.read_text(encoding="utf-8").replace(" ", "").replace("\n", ""))
            content_words = 0
            if content_files:
                content_words = len(content_files[0].read_text(encoding="utf-8").replace(" ", "").replace("\n", ""))
            
            chapters.append({
                "chapter": chapter_num,
                "name": chapter_name,
                "outline_words": outline_words,
                "content_words": content_words,
                "written": written,
            })
        
        return {
            "volume": volume.to_dict(),
            "is_current": state.get("progress", {}).get("current_volume") == volume_id,
            "chapters": chapters,
            "completion_rate": sum(1 for c in chapters if c["written"]) / len(chapters) * 100 if chapters else 0,
        }
    
    def set_current_volume(self, volume_id: int) -> Dict[str, Any]:
        """设置当前卷"""
        volumes = self._scan_volumes()
        
        if volume_id not in volumes:
            return {
                "status": "error",
                "message": f"卷 {volume_id} 不存在",
            }
        
        state = self._load_state()
        state["progress"]["current_volume"] = volume_id
        self._save_state(state)
        
        return {
            "status": "ok",
            "volume_id": volume_id,
            "message": f"已切换到第{volume_id}卷",
        }
    
    def complete_volume(self, volume_id: int) -> Dict[str, Any]:
        """完成卷"""
        volumes = self._scan_volumes()
        
        if volume_id not in volumes:
            return {
                "status": "error",
                "message": f"卷 {volume_id} 不存在",
            }
        
        volume = volumes[volume_id]
        
        # 检查是否所有章节都已完成
        status_data = self.get_volume_status(volume_id)
        if status_data["completion_rate"] < 100:
            return {
                "status": "error",
                "message": f"卷 {volume_id} 尚未完成所有章节（完成度：{status_data['completion_rate']:.1f}%）",
            }
        
        # 创建卷完成记录
        completion_file = self.outline_dir / volume.name / "VOLUME_COMPLETED.md"
        completion_file.write_text(
            f"# {volume.name} 完成记录\n\n"
            f"完成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"## 统计信息\n\n"
            f"- 章节数：{volume.chapter_count}\n"
            f"- 大纲字数：{volume.word_count}\n"
            f"- 状态：已完成\n",
            encoding="utf-8"
        )
        
        return {
            "status": "ok",
            "volume_id": volume_id,
            "message": f"第{volume_id}卷已完成！",
        }
    
    def get_volume_summary(self, volume_id: int) -> Optional[str]:
        """生成卷级大纲汇总"""
        volumes = self._scan_volumes()
        
        if volume_id not in volumes:
            return None
        
        volume = volumes[volume_id]
        volume_dir = self.outline_dir / volume.name
        
        summary = f"# {volume.name} 大纲汇总\n\n"
        summary += f"**状态**：{volume.status}\n"
        summary += f"**章节数**：{volume.chapter_count}\n"
        summary += f"**字数**：{volume.word_count}\n\n"
        
        # 汇总所有章节大纲
        for chapter_file in sorted(volume_dir.glob("第*章.md")):
            chapter_name = chapter_file.stem
            chapter_content = chapter_file.read_text(encoding="utf-8")
            
            summary += f"## {chapter_name}\n\n"
            summary += chapter_content
            summary += "\n\n---\n\n"
        
        return summary
