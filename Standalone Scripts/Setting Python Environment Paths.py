import os, subprocess, sys, urllib, re
from os.path import split, join
from os import path

def install_package(name):
    subprocess.call(['pip install',name],shell=True)

def ArcGIS_Version_Check():
    d = arcpy.GetInstallInfo()
    return d['Version']

def CMD_Writeout(paths):
    cmdline = ["cmd", "/q", "/k", "echo on"]
    cmd = subprocess.Popen(cmdline, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    batch = b"""
    setx PATH {}
    echo {}
    echo %PATH%
    exit
    """.format(paths, paths)
    cmd.stdin.write(batch)
    cmd.stdin.flush()
    result = cmd.stdout.read()
    print(result.decode())

def Download_File(url):
    INPUT_PATH = os.path.abspath('__file__')
    BASE_DIR = os.path.dirname(os.path.normpath(INPUT_PATH))
    python_file = os.path.join(BASE_DIR, "install-pip.py")
    urllib.urlretrieve(url,python_file)
    #subprocess.Popen(python_file, shell=True)
    #os.system('C:\Python27\ArcGIS10.3\Python {}'.format(os.path.basename(python_file)))
    os.startfile(python_file)

try:
    import arcpy
except ImportError:
    print """ArcGIS may not be installed on this PC since the arcpy python package failed to import.\n
    Here is the current version of Python that is running: {}\n
    If ArcMap is installed on your machine and the 64-bit Background Geoprocessing product was installed,  
    for some reason the 32 bit varient of python was executed over the 64 bit varient.""".format(sys.version)
    exit()

#.....................................................................
# Python Environmental Variable Paths for various versions of ArcGIS
#.....................................................................
SYS_PATHS_PYTHON32 = {
    '10.2': 'C:\Python27\ArcGIS10.2;C:\Python27\ArcGIS10.2\Scripts',
    '10.2.2': 'C:\Python27\ArcGIS10.2;C:\Python27\ArcGIS10.2\Scripts',
    '10.3': 'C:\Python27\ArcGIS10.3;C:\Python27\ArcGIS10.3\Scripts',
    '10.3.1': 'C:\Python27\ArcGIS10.3;C:\Python27\ArcGIS10.3\Scripts',
    '10.4': 'C:\Python27\ArcGIS10.4;C:\Python27\ArcGIS10.4\Scripts',
    '10.4.1': 'C:\Python27\ArcGIS10.4;C:\Python27\ArcGIS10.4\Scripts',
	'10.5': 'C:\Python27\ArcGIS10.5;C:\Python27\ArcGIS10.5\Scripts',
    '10.5.1': 'C:\Python27\ArcGIS10.5;C:\Python27\ArcGIS10.5\Scripts',
    '10.6': 'C:\Python27\ArcGIS10.6;C:\Python27\ArcGIS10.6\Scripts'
    }

SYS_PATHS_PYTHON64 = {
    '10.2': 'C:\Python27\ArcGISx6410.2;C:\Python27\ArcGISx6410.2\Scripts',
    '10.2.2': 'C:\Python27\ArcGISx6410.2;C:\Python27\ArcGISx6410.2\Scripts',
    '10.3': 'C:\Python27\ArcGISx6410.3;C:\Python27\ArcGISx6410.3\Scripts',
    '10.3.1': 'C:\Python27\ArcGISx6410.3;C:\Python27\ArcGISx6410.3\Scripts',
    '10.4': 'C:\Python27\ArcGISx6410.4;C:\Python27\ArcGISx6410.4\Scripts',
    '10.4.1': 'C:\Python27\ArcGISx6410.4;C:\Python27\ArcGISx6410.4\Scripts',
	'10.5': 'C:\Python27\ArcGISx6410.5;C:\Python27\ArcGISx6410.5\Scripts',
    '10.5.1': 'C:\Python27\ArcGISx6410.5;C:\Python27\ArcGISx6410.5\Scripts',
    '10.6': 'C:\Python27\ArcGISx6410.6;C:\Python27\ArcGISx6410.6\Scripts'
    }

#Name of package to install. If python package needs to be installed, change the varable to desired name.  Otherwise keep variable set to none.
package = raw_input('Type in the package name to install.\n\nIf you are not installing a package press OK and/or press enter: ')

#Get Environmental Variable paths
SYS_PATHS = (os.environ['Path']).split(';')

try:
    #Check to see which to see if running 32 bit python
    if sys.version.find("32 bit") > 0:
        ver = ArcGIS_Version_Check().split(".1")[0]
        paths = SYS_PATHS_PYTHON32[ver].split(';')
        if paths[0] in SYS_PATHS and paths[1] in SYS_PATHS:
            print "Environment Paths for Python 32bit are ok for ArcMap Version {}".format(ver)
        else:
            print "Python 32bit for ArcGIS {} is not set as a environment variable, fixing that now....".format(ver)
            print "ArcGIS Version: {} >>> Updating Environment Variables with new Python Paths.".format(ver)
            CMD_Writeout(SYS_PATHS_PYTHON32[ver])

    #Check to see which to see if running 64 bit python
    elif sys.version.find("64 bit") > 0:
        ver = ArcGIS_Version_Check().split(".1")[0]
        paths = SYS_PATHS_PYTHON64[ver].split(';')
        if paths[0] in SYS_PATHS and paths[1] in SYS_PATHS:
            print "Environment Paths for Python 64bit are ok for ArcMap Version {}".format(ver)
        else:
            print "Python 64bit for ArcGIS {} is not set as a environment variable, fixing that now....".format(ver)
            print "ArcGIS Version: {} >>> Updating Environment Variables with new Python Paths.".format(ver)
            CMD_Writeout(SYS_PATHS_PYTHON64[ver])

except Exception, e:
    # If an error occurred, print line number and error message
    import traceback, sys
    tb = sys.exc_info()[2]
    print "Line {}:".format(tb.tb_lineno,)
    print e.message

if package:
    try:
        import pip
        print "Installing the following Python package: {}".format(package)
        install_package(package)
    except ImportError:
        #print "The Python package, Pip, is not installed. \nPlease download the script from the following link: https://raw.github.com/pypa/pip/master/contrib/get-pip.py \nOnce downloaded, run the script to install"
        print "The Python package, pip, is not installed. \nDownloading from {} and installing package.  \nMore info on pip can be found here: {}".format("https://bootstrap.pypa.io/get-pip.py","https://pip.pypa.io/en/stable/user_guide/")
        Download_File("https://bootstrap.pypa.io/get-pip.py")
        print "Installing the following Python package: {}".format(package)
        install_package(package)

