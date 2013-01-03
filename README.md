This python program will sample data from a BB electronics data acquisition module 232 SDA12 through a USB adapter.

Should be runnable on either linux or windows (or cygwin), since it *should* select the right serial port.  Of course this assumes that you are communicating with the first port (COM1 or TTYUSB0).

To be able to run the script without sudo privileges, you need to add the user to the dialout group like:

    usermod -a -G dialout MY_USER_NAME   (as root, or with sudo)

...and then log out/log in or reboot for the changes to take effect

Running on Windows (I haven't tested this process yet, just guessing):

- Option 1:
    - Install a python interpreter: http://www.python.org/download/
    - Install numpy: http://scipy.org/Download
    - Install matplotlib: https://github.com/matplotlib/matplotlib/downloads/
    - Install pygtk: http://www.pygtk.org/downloads.html
 
- Option 2:
    - Install the Enthought python distribution which contains python, numpy, matplotlib, et al.
    - Install pygtk: http://www.pygtk.org/downloads.html

Running on Debian Linux:

- Install:

        sudo apt-get install python python-matplotlib python-numpy

