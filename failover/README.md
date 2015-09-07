Modify /etc/networking/ eth0.cfg
Add the floating address.
# The primary network interface
    auto eth0
    iface eth0 inet dhcp

    iface eth0:0 inet static
    address 10.9.248.10
    netmask 255.255.255.0

# Then you can run
    sudo ifup eth0:0