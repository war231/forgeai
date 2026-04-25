#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查点管理器

支持断点续传,包括:
1. 任务进度保存
2. 断点恢复
3. 任务状态追踪
"""

from __future__ import annotations

import json
import asyncio
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

from .logger import get_logger

logger = get_logger(__name__)


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


@dataclass
class Checkpoint:
    """检查点"""
    task_id: str
    task_type: str  # batch_generate, optimize, etc.
    status: TaskStatus
    
    # 进度信息
    total_steps: int = 0
    completed_steps: int = 0
    current_step: str = ""
    
    # 任务参数
    params: Dict[str, Any] = field(default_factory=dict)
    
    # 已完成的步骤结果
    completed_items: List[Dict[str, Any]] = field(default_factory=list)
    
    # 失败的步骤
    failed_items: List[Dict[str, Any]] = field(default_factory=list)
    
    # 时间信息
    created_at: str = ""
    updated_at: str = ""
    started_at: str = ""
    completed_at: str = ""
    
    # 错误信息
    last_error: Optional[str] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at
    
    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "status": self.status.value,
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "current_step": self.current_step,
            "params": self.params,
            "completed_items": self.completed_items,
            "failed_items": self.failed_items,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "last_error": self.last_error,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Checkpoint":
        return cls(
            task_id=data["task_id"],
            task_type=data["task_type"],
            status=TaskStatus(data["status"]),
            total_steps=data.get("total_steps", 0),
            completed_steps=data.get("completed_steps", 0),
            current_step=data.get("current_step", ""),
            params=data.get("params", {}),
            completed_items=data.get("completed_items", []),
            failed_items=data.get("failed_items", []),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            started_at=data.get("started_at", ""),
            completed_at=data.get("completed_at", ""),
            last_error=data.get("last_error"),
            metadata=data.get("metadata", {}),
        )
    
    @property
    def progress_percent(self) -> float:
        """进度百分比"""
        if self.total_steps == 0:
            return 0.0
        return (self.completed_steps / self.total_steps) * 100
    
    @property
    def is_resumable(self) -> bool:
        """是否可恢复"""
        return self.status in [TaskStatus.PAUSED, TaskStatus.FAILED]


class CheckpointManager:
    """检查点管理器"""
    
    def __init__(self, checkpoint_dir: Optional[Path] = None):
        self.checkpoint_dir = checkpoint_dir or Path(".forgeai/checkpoints")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_checkpoint_path(self, task_id: str) -> Path:
        """获取检查点文件路径"""
        return self.checkpoint_dir / f"{task_id}.json"
    
    def create_checkpoint(
        self,
        task_id: str,
        task_type: str,
        total_steps: int,
        params: Optional[Dict[str, Any]] = None,
    ) -> Checkpoint:
        """创建检查点"""
        checkpoint = Checkpoint(
            task_id=task_id,
            task_type=task_type,
            status=TaskStatus.PENDING,
            total_steps=total_steps,
            params=params or {},
        )
        
        self.save_checkpoint(checkpoint)
        logger.info(f"创建检查点: {task_id} (类型: {task_type}, 总步骤: {total_steps})")
        
        return checkpoint
    
    def save_checkpoint(self, checkpoint: Checkpoint) -> None:
        """保存检查点"""
        checkpoint.updated_at = datetime.now().isoformat()
        
        path = self._get_checkpoint_path(checkpoint.task_id)
        path.write_text(
            json.dumps(checkpoint.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        logger.debug(f"保存检查点: {checkpoint.task_id} (进度: {checkpoint.progress_percent:.1f}%)")
    
    def load_checkpoint(self, task_id: str) -> Optional[Checkpoint]:
        """加载检查点"""
        path = self._get_checkpoint_path(task_id)
        
        if not path.exists():
            return None
        
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            checkpoint = Checkpoint.from_dict(data)
            logger.info(f"加载检查点: {task_id} (状态: {checkpoint.status.value}, 进度: {checkpoint.progress_percent:.1f}%)")
            return checkpoint
        except Exception as e:
            logger.error(f"加载检查点失败: {task_id}, 错误: {e}")
            return None
    
    def delete_checkpoint(self, task_id: str) -> None:
        """删除检查点"""
        path = self._get_checkpoint_path(task_id)
        if path.exists():
            path.unlink()
            logger.info(f"删除检查点: {task_id}")
    
    def list_checkpoints(
        self,
        task_type: Optional[str] = None,
        status: Optional[TaskStatus] = None,
    ) -> List[Checkpoint]:
        """列出检查点"""
        checkpoints = []
        
        for path in self.checkpoint_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                checkpoint = Checkpoint.from_dict(data)
                
                # 过滤
                if task_type and checkpoint.task_type != task_type:
                    continue
                if status and checkpoint.status != status:
                    continue
                
                checkpoints.append(checkpoint)
            except Exception as e:
                logger.warning(f"加载检查点失败: {path}, 错误: {e}")
        
        # 按更新时间排序
        checkpoints.sort(key=lambda x: x.updated_at, reverse=True)
        
        return checkpoints
    
    def start_task(self, task_id: str) -> Optional[Checkpoint]:
        """开始任务"""
        checkpoint = self.load_checkpoint(task_id)
        
        if not checkpoint:
            logger.error(f"检查点不存在: {task_id}")
            return None
        
        checkpoint.status = TaskStatus.RUNNING
        checkpoint.started_at = datetime.now().isoformat()
        
        self.save_checkpoint(checkpoint)
        logger.info(f"开始任务: {task_id}")
        
        return checkpoint
    
    def complete_step(
        self,
        task_id: str,
        step_name: str,
        result: Optional[Dict[str, Any]] = None,
    ) -> None:
        """完成步骤"""
        checkpoint = self.load_checkpoint(task_id)
        
        if not checkpoint:
            logger.error(f"检查点不存在: {task_id}")
            return
        
        checkpoint.completed_steps += 1
        checkpoint.current_step = step_name
        
        if result:
            checkpoint.completed_items.append({
                "step": step_name,
                "result": result,
                "completed_at": datetime.now().isoformat(),
            })
        
        self.save_checkpoint(checkpoint)
        logger.info(f"完成步骤: {task_id}/{step_name} ({checkpoint.completed_steps}/{checkpoint.total_steps})")
    
    def fail_step(
        self,
        task_id: str,
        step_name: str,
        error: str,
    ) -> None:
        """失败步骤"""
        checkpoint = self.load_checkpoint(task_id)
        
        if not checkpoint:
            logger.error(f"检查点不存在: {task_id}")
            return
        
        checkpoint.failed_items.append({
            "step": step_name,
            "error": error,
            "failed_at": datetime.now().isoformat(),
        })
        checkpoint.last_error = error
        
        self.save_checkpoint(checkpoint)
        logger.error(f"步骤失败: {task_id}/{step_name}, 错误: {error}")
    
    def pause_task(self, task_id: str) -> None:
        """暂停任务"""
        checkpoint = self.load_checkpoint(task_id)
        
        if not checkpoint:
            logger.error(f"检查点不存在: {task_id}")
            return
        
        checkpoint.status = TaskStatus.PAUSED
        self.save_checkpoint(checkpoint)
        
        logger.info(f"暂停任务: {task_id} (进度: {checkpoint.progress_percent:.1f}%)")
    
    def complete_task(self, task_id: str) -> None:
        """完成任务"""
        checkpoint = self.load_checkpoint(task_id)
        
        if not checkpoint:
            logger.error(f"检查点不存在: {task_id}")
            return
        
        checkpoint.status = TaskStatus.COMPLETED
        checkpoint.completed_at = datetime.now().isoformat()
        
        self.save_checkpoint(checkpoint)
        
        logger.info(
            f"完成任务: {task_id} "
            f"(完成步骤: {checkpoint.completed_steps}/{checkpoint.total_steps}, "
            f"失败步骤: {len(checkpoint.failed_items)})"
        )
    
    def fail_task(self, task_id: str, error: str) -> None:
        """失败任务"""
        checkpoint = self.load_checkpoint(task_id)
        
        if not checkpoint:
            logger.error(f"检查点不存在: {task_id}")
            return
        
        checkpoint.status = TaskStatus.FAILED
        checkpoint.last_error = error
        checkpoint.completed_at = datetime.now().isoformat()
        
        self.save_checkpoint(checkpoint)
        
        logger.error(f"任务失败: {task_id}, 错误: {error}")
    
    def resume_task(self, task_id: str) -> Optional[Checkpoint]:
        """恢复任务"""
        checkpoint = self.load_checkpoint(task_id)
        
        if not checkpoint:
            logger.error(f"检查点不存在: {task_id}")
            return None
        
        if not checkpoint.is_resumable:
            logger.error(f"任务不可恢复: {task_id} (状态: {checkpoint.status.value})")
            return None
        
        checkpoint.status = TaskStatus.RUNNING
        checkpoint.updated_at = datetime.now().isoformat()
        
        self.save_checkpoint(checkpoint)
        
        logger.info(
            f"恢复任务: {task_id} "
            f"(从步骤 {checkpoint.completed_steps}/{checkpoint.total_steps} 继续)"
        )
        
        return checkpoint
    
    def get_resumable_tasks(self) -> List[Checkpoint]:
        """获取可恢复的任务"""
        return self.list_checkpoints(status=TaskStatus.PAUSED) + \
               self.list_checkpoints(status=TaskStatus.FAILED)


class ResumableTask:
    """可恢复任务基类"""
    
    def __init__(self, checkpoint_manager: CheckpointManager):
        self.checkpoint_manager = checkpoint_manager
        self.checkpoint: Optional[Checkpoint] = None
    
    async def execute(
        self,
        task_id: str,
        task_type: str,
        steps: List[Dict[str, Any]],
        params: Optional[Dict[str, Any]] = None,
        resume: bool = True,
    ) -> Checkpoint:
        """
        执行可恢复任务
        
        Args:
            task_id: 任务ID
            task_type: 任务类型
            steps: 步骤列表
            params: 任务参数
            resume: 是否从断点恢复
        
        Returns:
            检查点
        """
        # 尝试加载已有检查点
        if resume:
            self.checkpoint = self.checkpoint_manager.load_checkpoint(task_id)
        
        # 创建新检查点
        if not self.checkpoint:
            self.checkpoint = self.checkpoint_manager.create_checkpoint(
                task_id=task_id,
                task_type=task_type,
                total_steps=len(steps),
                params=params,
            )
        
        # 开始任务
        self.checkpoint = self.checkpoint_manager.start_task(task_id)
        
        # 执行步骤
        start_index = self.checkpoint.completed_steps
        
        for i, step in enumerate(steps[start_index:], start=start_index):
            step_name = step.get("name", f"step_{i}")
            
            try:
                # 执行步骤
                result = await self._execute_step(step, self.checkpoint)
                
                # 记录完成
                self.checkpoint_manager.complete_step(
                    task_id, step_name, result
                )
                
                # 重新加载检查点
                self.checkpoint = self.checkpoint_manager.load_checkpoint(task_id)
            
            except Exception as e:
                # 记录失败
                self.checkpoint_manager.fail_step(task_id, step_name, str(e))
                
                # 暂停任务
                self.checkpoint_manager.pause_task(task_id)
                
                # 重新加载检查点
                self.checkpoint = self.checkpoint_manager.load_checkpoint(task_id)
                
                raise
        
        # 完成任务
        self.checkpoint_manager.complete_task(task_id)
        self.checkpoint = self.checkpoint_manager.load_checkpoint(task_id)
        
        return self.checkpoint
    
    async def _execute_step(
        self,
        step: Dict[str, Any],
        checkpoint: Checkpoint,
    ) -> Optional[Dict[str, Any]]:
        """执行单个步骤(子类实现)"""
        raise NotImplementedError
