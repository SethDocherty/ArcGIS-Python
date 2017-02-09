import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/' + '../..'))
from helpers import import_test 

for item in sys.path:
    print item

print "\n"

import_test.hello()







