from fabric.api import *
import ConfigParser

def deploy(server):
	env.user = 'root'
        # Fetch some values from the config file
        # @TODO fix this so that fabfile doesn't depend on ConfigParser at all
        config = ConfigParser.RawConfigParser()
        config.read('config/felicity.ini')
	# The Duplicity passphrase, for decrypting during restore
	passphrase = config.get('Felicity', 'passphrase')
	# Where should we send the report to?
	email = config.get('Felicity', 'email')
	# Where are the backups?
	backupprovider = config.get('Felicity', 'backupprovider')

	# Upload scripts
        scripts = ['backup_list_buckets', 'backup_list_bucket_keys', 'backup_list_containers', 'backup_restore_wrapper', 'backup_restore', 'firewall']
        for script in scripts:
		put('scripts/' + script, '/usr/local/bin/' + script, mode=0755)

        # Store creds in a file for using by the backup restore script
        creds = []
        if backupprovider == "Amazon":
                creds.append("export AWS_ACCESS_KEY_ID=%s\n" % config.get('Amazon', 'user'))
                creds.append("export AWS_SECRET_ACCESS_KEY=%s\n" % config.get('Amazon', 'key'))
        if backupprovider == "Rackspace":
                creds.append("export CLOUDFILES_USERNAME=%s\n" % config.get('Rackspace', 'user'))
                creds.append("export CLOUDFILES_APIKEY=%s\n" % config.get('Rackspace','key'))

        creds.append("export PASSPHRASE=%s\n" % passphrase)
        creds_file = open('scripts/backup_restore_creds', 'w')
        creds_file.writelines(creds)
        creds_file.close()

	put('scripts/backup_restore_creds', '/usr/local/etc/backup_restore_creds', mode=0755)

	# Grab python-cloudfiles
	run('git clone git://github.com/rackspace/python-cloudfiles.git /opt/python-cloudfiles', pty=True)
	with cd('/opt/python-cloudfiles/'):
		run('python setup.py install') 

        # Setting self-destruct for 48 hours
	run('echo "halt" | at now + 2 days', pty=True)

	# Disabling password authentication in SSH
	run('sed -i -r -e "s/^[ #]*(PasswordAuthentication).*/PasswordAuthentication no/" /etc/ssh/sshd_config', pty=True)
	run('/etc/init.d/ssh restart', pty=True)

	# Setting a firewall
	run('/usr/local/bin/firewall start', pty=True)
	# Preparing restore script to run
	run('/usr/local/bin/backup_restore_wrapper %s %s %s' % (server, email, backupprovider), pty=True)

