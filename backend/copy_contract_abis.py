#!/usr/bin/env python3
"""
Script to copy contract ABIs from artifacts to backend for easier access
"""
import os
import json
import shutil
from pathlib import Path

def copy_contract_abis():
    """Copy contract ABIs from artifacts to backend contracts directory"""
    
    # Get paths
    backend_dir = Path(__file__).parent
    contracts_artifacts_dir = backend_dir.parent / "contracts" / "artifacts" / "contracts"
    backend_contracts_dir = backend_dir / "contracts"
    
    # Create backend contracts directory if it doesn't exist
    backend_contracts_dir.mkdir(exist_ok=True)
    
    # Contract names to copy
    contracts = ["DonationRegistry", "TransparencyVerifier", "YtiliToken", "YtiliGovernance"]
    
    print("Copying contract ABIs...")
    
    for contract_name in contracts:
        try:
            # Source path
            source_file = contracts_artifacts_dir / f"{contract_name}.sol" / f"{contract_name}.json"
            
            # Destination path
            dest_file = backend_contracts_dir / f"{contract_name}.json"
            
            if source_file.exists():
                # Copy the file
                shutil.copy2(source_file, dest_file)
                print(f"✅ Copied {contract_name}.json")
                
                # Verify ABI exists in the copied file
                with open(dest_file, 'r') as f:
                    contract_data = json.load(f)
                    if 'abi' in contract_data:
                        abi_functions = len([item for item in contract_data['abi'] if item.get('type') == 'function'])
                        print(f"   📋 ABI contains {abi_functions} functions")
                    else:
                        print(f"   ⚠️  Warning: No ABI found in {contract_name}.json")
            else:
                print(f"❌ Source file not found: {source_file}")
                
        except Exception as e:
            print(f"❌ Error copying {contract_name}: {e}")
    
    print("\nABI copy completed!")
    print(f"ABIs copied to: {backend_contracts_dir}")

if __name__ == "__main__":
    copy_contract_abis()
