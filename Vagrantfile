# -*- mode: ruby -*-
# vi: set ft=ruby :

bootstrap_script = <<EOT
sudo apt-get update
sudo apt-get install -y build-essential ansible
EOT

ansible_script = <<EOT
ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -i /var/www/pilbox/provisioning/vagrant /var/www/pilbox/provisioning/playbook.yml
EOT

Vagrant.configure("2") do |config|
  # Every Vagrant virtual environment requires a box to build off of.
  config.vm.box = "bento/ubuntu-16.04"

  # Disable random key creation
  config.ssh.insert_key = false

  # Create a public network, which generally matched to bridged network.
  # Bridged networks make the machine appear as another physical device on
  # your network.
  config.vm.network :private_network, :ip => "192.168.100.100"

  # Share an additional folder to the guest VM. The first argument is
  # the path on the host to the actual folder. The second argument is
  # the path on the guest to mount the folder. And the optional third
  # argument is a set of non-required options.
  config.vm.synced_folder ".", "/var/www/pilbox", :owner => 'vagrant'

  # The machine performs its own provisioning.
  config.vm.provision 'shell', inline: bootstrap_script, privileged: false
  config.vm.provision 'file', {
    source: '~/.vagrant.d/insecure_private_key',
    destination: '~/.ssh/id_rsa',
  }
  config.vm.provision 'shell', inline: ansible_script, privileged: false
end
