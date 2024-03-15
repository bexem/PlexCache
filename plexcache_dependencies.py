import subprocess

def get_missing_dependencies():
    with open('requirements.txt') as f:
        required_packages = f.read().splitlines()
    
    missing_dependencies = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_dependencies.append(package)
    
    return missing_dependencies

def install_dependencies(dependencies):
    if dependencies:
        subprocess.call(["pip", "install"] + dependencies, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

if __name__ == "__main__":
    missing_deps = get_missing_dependencies()
    if missing_deps:
        print(f"Warning, missing dependencies: {', '.join(missing_deps)}")
        print(f"Installing {missing_deps}...")
        install_dependencies(missing_deps)
        print(f"{missing_deps} installed.")