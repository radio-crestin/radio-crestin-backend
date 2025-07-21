import os
import pkgutil

# Get the directory of this __init__.py file
package_dir = os.path.dirname(__file__)

# Iterate over all subdirectories and import them dynamically
for _, module_name, _ in pkgutil.iter_modules([package_dir]):
    __import__(f"{__name__}.{module_name}")

# Clean up namespace
del os, pkgutil, package_dir, module_name
