CAMERA_INDEX = 0        
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
HFOV_DEG = 70.0          


CAMERA_MATRIX = None
DIST_COEFFS = None        


MARKER_SIZE_M = 0.15      
TARGET_ID = 0             
ARUCO_DICTIONARY = "DICT_5X5_50"   

CMD_VEL_TOPIC = "/cmd_vel"   


DOCKING_PARAMS = {
    "dock_distance": 0.35,     
    "angle_tolerance_deg": 4.0,  
    "realign_factor": 2.5,     
    "max_linear": 0.15,       
    "min_linear": 0.04,        
    "max_angular": 0.5,       
    "min_angular": 0.08,      
    "search_angular": 0.3,    
    "kp_angular": 1.2,
    "kp_linear": 0.5,
    "lost_timeout": 1.0,      
}



