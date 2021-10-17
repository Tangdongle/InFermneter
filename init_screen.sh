#! /usr/bin/bash
# /etc/init.d/init_screen.sh
### BEGIN INIT INFO
# Provides:          init_screen.sh
# Required-Start:    $remote_fs $syslog
# Required-Stop:     $remote_fs $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Start daemon at boot time
# Description:       Enable service provided by daemon.
### END INIT INFO

runuser -l pi -c "screen -dmS master exec /usr/bin/bash"
