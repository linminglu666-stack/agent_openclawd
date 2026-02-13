from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .definition import (
    Profession,
    ProfessionCategory,
    ProfessionConfig,
    CollaborationConfig,
    Skill,
    BUILTIN_PROFESSIONS,
)


class ProfessionSystem:
    def __init__(self):
        self._professions: Dict[str, Profession] = {}
        self._category_index: Dict[ProfessionCategory, List[str]] = {}
        self._task_type_index: Dict[str, List[str]] = {}
        self._skill_index: Dict[str, List[str]] = {}
        
        self._load_builtin_professions()
    
    def _load_builtin_professions(self) -> None:
        for prof_data in BUILTIN_PROFESSIONS:
            profession = self._dict_to_profession(prof_data)
            self._register_profession(profession)
    
    def _dict_to_profession(self, data: Dict[str, Any]) -> Profession:
        skills = [
            Skill(
                name=s["name"],
                level=s["level"],
                description=s.get("description", ""),
            )
            for s in data.get("skills", [])
        ]
        
        collab_data = data.get("collaboration", {})
        collaboration = CollaborationConfig(
            upstream=collab_data.get("upstream", []),
            downstream=collab_data.get("downstream", []),
            review_required=collab_data.get("review_required", False),
            review_by=collab_data.get("review_by", []),
        )
        
        config_data = data.get("config", {})
        config = ProfessionConfig(
            preferred_model=config_data.get("preferred_model", "gpt-4"),
            max_concurrent_tasks=config_data.get("max_concurrent_tasks", 3),
            timeout_multiplier=config_data.get("timeout_multiplier", 1.0),
            quality_threshold=config_data.get("quality_threshold", 0.85),
            retry_policy=config_data.get("retry_policy", "exponential_backoff"),
            max_retries=config_data.get("max_retries", 3),
        )
        
        return Profession(
            profession_id=data["profession_id"],
            name=data["name"],
            category=ProfessionCategory(data.get("category", "general")),
            description=data.get("description", ""),
            skills=skills,
            task_types=data.get("task_types", []),
            collaboration=collaboration,
            config=config,
            tags=data.get("tags", []),
        )
    
    def _register_profession(self, profession: Profession) -> None:
        self._professions[profession.profession_id] = profession
        
        if profession.category not in self._category_index:
            self._category_index[profession.category] = []
        self._category_index[profession.category].append(profession.profession_id)
        
        for task_type in profession.task_types:
            if task_type not in self._task_type_index:
                self._task_type_index[task_type] = []
            self._task_type_index[task_type].append(profession.profession_id)
        
        for skill in profession.skills:
            if skill.name not in self._skill_index:
                self._skill_index[skill.name] = []
            self._skill_index[skill.name].append(profession.profession_id)
    
    def register_profession(self, profession: Profession) -> None:
        if profession.profession_id in self._professions:
            raise ValueError(f"Profession already exists: {profession.profession_id}")
        self._register_profession(profession)
    
    def register_from_dict(self, data: Dict[str, Any]) -> Profession:
        profession = self._dict_to_profession(data)
        self.register_profession(profession)
        return profession
    
    def get_profession(self, profession_id: str) -> Optional[Profession]:
        return self._professions.get(profession_id)
    
    def list_professions(
        self,
        category: Optional[ProfessionCategory] = None,
    ) -> List[Profession]:
        if category:
            ids = self._category_index.get(category, [])
            return [self._professions[iid] for iid in ids if iid in self._professions]
        return list(self._professions.values())
    
    def find_by_task_type(self, task_type: str) -> List[Profession]:
        ids = self._task_type_index.get(task_type, [])
        return [self._professions[iid] for iid in ids if iid in self._professions]
    
    def find_by_skill(
        self,
        skill_name: str,
        min_level: int = 1,
    ) -> List[Profession]:
        ids = self._skill_index.get(skill_name, [])
        result = []
        for iid in ids:
            prof = self._professions.get(iid)
            if prof and prof.get_skill_level(skill_name) >= min_level:
                result.append(prof)
        return result
    
    def find_best_for_task(
        self,
        task_type: str,
        required_skills: Optional[Dict[str, int]] = None,
    ) -> Optional[Profession]:
        candidates = self.find_by_task_type(task_type)
        
        if not candidates:
            return None
        
        if not required_skills:
            return candidates[0]
        
        best = None
        best_score = -1
        
        for prof in candidates:
            score = sum(
                prof.get_skill_level(skill) * weight
                for skill, weight in required_skills.items()
            )
            if score > best_score:
                best_score = score
                best = prof
        
        return best
    
    def get_collaboration_chain(
        self,
        profession_id: str,
        direction: str = "downstream",
    ) -> List[str]:
        profession = self.get_profession(profession_id)
        if not profession:
            return []
        
        if direction == "downstream":
            return profession.get_downstream_professions()
        elif direction == "upstream":
            return profession.get_upstream_professions()
        return []
    
    def get_full_collaboration_graph(self) -> Dict[str, Dict[str, List[str]]]:
        return {
            prof_id: {
                "upstream": prof.get_upstream_professions(),
                "downstream": prof.get_downstream_professions(),
            }
            for prof_id, prof in self._professions.items()
        }
    
    def validate_collaboration(self, source_id: str, target_id: str) -> bool:
        source = self.get_profession(source_id)
        if not source:
            return False
        
        return target_id in source.get_downstream_professions() or \
               target_id in source.get_upstream_professions()
    
    def get_profession_count(self) -> int:
        return len(self._professions)
    
    def get_categories(self) -> List[ProfessionCategory]:
        return list(self._category_index.keys())
