import os, sys

# Starting here: services/collector/tests
# Go up three levels to reach your repo root (where shared/ & services/ live)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)