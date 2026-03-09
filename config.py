class Settings:
    
    REF_DATABASE_PATH: str = "storage/db/reference_curves.db"
    
    REF_k: float = 5
    REF_phi: float = 0.2
    REF_mu: float = 1
    REF_B: float = 1
    REF_ct: float = 4e-5
    REF_P0: float = 300
    
    
    MIN_POINTS: int = 20

settings = Settings()
