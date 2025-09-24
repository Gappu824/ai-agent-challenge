"""
Configuration settings for AI Agent Bank Statement Parser
"""

import os
from pathlib import Path
from typing import Dict, Any


class Config:
    """Configuration class for the agent"""
    
    # API Configuration
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    GEMINI_MODEL = 'gemini-1.5-pro'
    
    # Agent Configuration
    MAX_ATTEMPTS = 3
    TIMEOUT_SECONDS = 60
    
    # File Paths
    BASE_DIR = Path(__file__).parent
    DATA_DIR = BASE_DIR / "data"
    PARSERS_DIR = BASE_DIR / "custom_parsers"
    TESTS_DIR = BASE_DIR / "tests"
    
    # Supported Banks
    SUPPORTED_BANKS = [
        'icici',
        'sbi',
        'hdfc',
        'axis',
        'kotak'
    ]
    
    # Parser Contract
    REQUIRED_COLUMNS = [
        'Date',
        'Description', 
        'Debit Amt',
        'Credit Amt',
        'Balance'
    ]
    
    # LLM Configuration
    LLM_SETTINGS = {
        'temperature': 0.1,  # Low temperature for consistent code generation
        'max_tokens': 4000,
        'top_p': 0.8,
    }
    
    # Safety Settings for Gemini
    SAFETY_SETTINGS = {
        'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
        'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE', 
        'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
        'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE',
    }
    
    @classmethod
    def get_bank_paths(cls, bank_name: str) -> Dict[str, Path]:
        """Get file paths for a specific bank"""
        bank_dir = cls.DATA_DIR / bank_name
        return {
            'pdf_path': bank_dir / f"{bank_name}_sample.pdf",
            'csv_path': bank_dir / f"{bank_name}_sample.csv",
            'parser_path': cls.PARSERS_DIR / f"{bank_name}_parser.py"
        }
    
    @classmethod
    def validate_setup(cls) -> Dict[str, Any]:
        """Validate configuration setup"""
        issues = []
        warnings = []
        
        # Check API key
        if not cls.GEMINI_API_KEY:
            issues.append("GEMINI_API_KEY not set")
        
        # Check directories
        for dir_path in [cls.DATA_DIR, cls.PARSERS_DIR]:
            if not dir_path.exists():
                warnings.append(f"Directory will be created: {dir_path}")
        
        # Check supported banks data
        for bank in cls.SUPPORTED_BANKS:
            paths = cls.get_bank_paths(bank)
            if not paths['pdf_path'].parent.exists():
                warnings.append(f"Data directory missing for {bank}")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        }
    
    @classmethod
    def create_directories(cls):
        """Create necessary directories"""
        directories = [
            cls.DATA_DIR,
            cls.PARSERS_DIR,
            cls.TESTS_DIR
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Create bank-specific directories
        for bank in cls.SUPPORTED_BANKS:
            bank_dir = cls.DATA_DIR / bank
            bank_dir.mkdir(exist_ok=True)


# Global configuration instance
config = Config()


def get_config() -> Config:
    """Get global configuration instance"""
    return config


def validate_environment() -> bool:
    """Validate environment setup"""
    validation = config.validate_setup()
    
    if not validation['valid']:
        print("❌ Configuration issues:")
        for issue in validation['issues']:
            print(f"   - {issue}")
        return False
    
    if validation['warnings']:
        print("⚠️  Configuration warnings:")
        for warning in validation['warnings']:
            print(f"   - {warning}")
    
    return True


if __name__ == "__main__":
    # Run configuration validation
    print("🔧 Configuration Validation")
    print("-" * 30)
    
    validation = config.validate_setup()
    
    print(f"Valid: {validation['valid']}")
    
    if validation['issues']:
        print("Issues:")
        for issue in validation['issues']:
            print(f"  - {issue}")
    
    if validation['warnings']:
        print("Warnings:")
        for warning in validation['warnings']:
            print(f"  - {warning}")
    
    print(f"\nSupported banks: {', '.join(config.SUPPORTED_BANKS)}")
    print(f"Required columns: {', '.join(config.REQUIRED_COLUMNS)}")
    
    # Show paths
    print(f"\nDirectory paths:")
    print(f"  Base: {config.BASE_DIR}")
    print(f"  Data: {config.DATA_DIR}")
    print(f"  Parsers: {config.PARSERS_DIR}")
    
    # Create directories
    config.create_directories()
    print("\n✅ Configuration validation complete")
    
    # Show example bank paths
    if len(config.SUPPORTED_BANKS) > 0:
        example_bank = config.SUPPORTED_BANKS[0]
        paths = config.get_bank_paths(example_bank)
        print(f"\nExample paths for {example_bank}:")
        for key, path in paths.items():
            print(f"  {key}: {path}")
    
    print(f"\nAPI Configuration:")
    print(f"  Model: {config.GEMINI_MODEL}")
    print(f"  API Key Set: {'✅' if config.GEMINI_API_KEY else '❌'}")
    print(f"  Max Attempts: {config.MAX_ATTEMPTS}")
    print(f"  Timeout: {config.TIMEOUT_SECONDS}s")
    
    print("\n" + "="*50)
    print("Configuration setup complete! 🎉")
    print("\nNext steps:")
    print("1. Set GEMINI_API_KEY environment variable")
    print("2. Copy your PDF and CSV files to data/icici/")
    print("3. Run: python agent.py --target icici")