from  dataclasses import dataclass, field
from py_trees.behaviour import Behaviour
from py_trees.composites import Composite,Sequence
from abc import ABC,abstractmethod
from typing import List,ClassVar,Set,Dict
import re

@dataclass
class BehaviorBase(Behaviour,ABC):
    type_name: ClassVar[str] = field(default=None)

    @classmethod
    def get_type_info(cls):
        if cls.type_name is None:
            return cls.__name__
        return cls.type_name
    
    def update(self):
        return


@dataclass(kw_only=True)
class BehaviorModule(BehaviorBase,ABC):
    input_port_names: ClassVar[Set[str]] = field(default=set())
    output_port_names: ClassVar[Set[str]] = field(default=set())
    input_ports: Dict[str,str] = field(default_factory=dict)
    output_ports: Dict[str,str] = field(default_factory=dict)

    @staticmethod
    def _check_ports(decl_set:set,def_dict:dict):
            def_set = set(def_dict.keys())
            if not def_set.issuperset(decl_set):
                raise ValueError(f"Missing ports: {decl_set - def_set}")
            undecl_keys = def_set - decl_set
            if len(undecl_keys) > 0:
                print(f"WARNING: Undeclared ports: {undecl_keys}")
                for key in undecl_keys:
                    del def_dict[key]
    def __post_init__(self):
        if len(self.input_port_names.intersection(self.output_port_names)) > 0:
            raise ValueError(f"Duplicate ports: {self.input_port_names.intersection(self.output_port_names)}")
        self._check_ports(self.__class__.input_port_names,self.input_ports)
        self._check_ports(self.__class__.output_port_names,self.output_ports)

    def get_port_map(self):
        return {**self.input_ports,**self.output_ports}

@dataclass
class BehaviorModuleCollection(Composite,BehaviorModule):
    output_port_values : Dict[str,str] = field(default_factory=dict)
    children: List[BehaviorModule] = field(default_factory=list)
    out_children: List[BehaviorModule] = field(default_factory=list,init=False)

    def __post_init__(self):
        super().__post_init__()
        from .instruction import ScriptInstruction
        ref_set = set(self.output_port_values.keys())
        decl_set = set(self.output_port_names)
        if not decl_set.issuperset(ref_set):
            raise ValueError(f"Missing ports values: {ref_set - decl_set}")
        undecl_keys = ref_set - decl_set
        if len(undecl_keys) > 0:
            print(f"WARNING: Undeclared ports: {undecl_keys}")
            for key in undecl_keys:
                del self.output_port_values[key]
        pattern = r"^\{([a-zA-Z_][a-zA-Z0-9_]*)\}$"
        
        for port_name in self.output_port_names:
            value = self.output_port_values[port_name]
            if isinstance(value,str):
                key_match = re.fullmatch(pattern,value)
                if isinstance(key_match,re.Match):
                    value = key_match.group(1)
            else:
                raise ValueError(f"Invalid output port value: {value}")
            self.out_children.append(ScriptInstruction(code=f" {port_name}:={value} "))

    def get_port_map(self):
        return {**self.input_ports,**self.output_ports}

    def iterate(self):
        for child in self.children:
            yield child
        for child in self.out_children:
            yield child

@dataclass
class BehaviorModuleSequence(Sequence,BehaviorModuleCollection):
    pass