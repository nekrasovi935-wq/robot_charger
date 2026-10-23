import math
from enum import Enum


class State(Enum):
    SEARCHING = "SEARCHING"      
    ALIGNING = "ALIGNING"        
    APPROACHING = "APPROACHING"  
    DOCKED = "DOCKED"            


class DockingLogic:
    def __init__(self, **params):
        self.state = State.SEARCHING
        self._last_seen = -1e9
        self._last_bearing = 0.0

        self.dock_distance = 0.35                  
        self.angle_tolerance = math.radians(4.0)  
        self.realign_factor = 2.5
        self.max_linear = 0.15                     
        self.min_linear = 0.04                     
        self.max_angular = 0.5                     
        self.min_angular = 0.08                    
        self.search_angular = 0.3                  
        self.kp_angular = 1.2
        self.kp_linear = 0.5
        self.lost_timeout = 1.0                    

        for name, value in params.items():
            if name == "angle_tolerance_deg":
                self.angle_tolerance = math.radians(value)
            elif hasattr(self, name) and not name.startswith("_") and name != "state":
                setattr(self, name, value)
            else:
                raise TypeError(f"Неизвестный параметр DockingLogic: {name}")

    def reset(self):
       
        self.state = State.SEARCHING
        self._last_seen = -1e9
        self._last_bearing = 0.0

    @staticmethod
    def _clamp(value, lo, hi):
        
        mag = min(max(abs(value), lo), hi)
        return math.copysign(mag, value) if value != 0 else 0.0

    def step(self, pose, now):
       
        if self.state == State.DOCKED:
            return self.state, 0.0, 0.0

       
        if pose is not None and not (
            math.isfinite(pose.distance) and math.isfinite(pose.bearing)
        ):
            pose = None

        
        if pose is None:
            
            if (
                self.state in (State.ALIGNING, State.APPROACHING)
                and now - self._last_seen < self.lost_timeout
            ):
                return self.state, 0.0, 0.0
            
            self.state = State.SEARCHING
            direction = -1.0 if self._last_bearing > 0 else 1.0
            return self.state, 0.0, direction * self.search_angular

        self._last_seen = now
        self._last_bearing = pose.bearing

       
        if pose.distance <= self.dock_distance:
            self.state = State.DOCKED
            return self.state, 0.0, 0.0

       
        limit = self.angle_tolerance * (
            self.realign_factor if self.state == State.APPROACHING else 1.0
        )

       
        if abs(pose.bearing) > limit:
            self.state = State.ALIGNING
            w = -self._clamp(
                self.kp_angular * pose.bearing, self.min_angular, self.max_angular
            )
            return self.state, 0.0, w

        
        self.state = State.APPROACHING
        v = self.kp_linear * (pose.distance - self.dock_distance)
        v = min(max(v, self.min_linear), self.max_linear)
        w = -self._clamp(self.kp_angular * pose.bearing, 0.0, self.max_angular)
        return self.state, v, w