'admin':
    group.present:
        - system: True

'ansible':
    user.present:
        - shell: '/bin/bash'
        - password: ansible
        - groups:
            - admin
        - require:
            - group: 'admin'

'/etc/sudoers.d':
    file.directory:
        - user: 'root'
        - group: 'root'
        - dir_mode: 770

'/etc/sudoers':
    file.managed:
        - source: 'salt://files/etc/sudoers'
        - user: 'root'
        - group: 'root'
        - mode: 440

'/home/ansible/.ssh':
    file.directory:
        - user: 'ansible'
        - group: 'ansible'
        - dir_mode: 700
        - require:
            - user: 'ansible'

{% for authorized_key in salt['cmd.run']('cat /home/vagrant/.ssh/authorized_keys').splitlines() %}
'{{ authorized_key }}':
    ssh_auth.present:
        - user: 'ansible'
        - enc: 'ssh-rsa'
{% endfor %}

'deb_pkgs':
    pkg.installed:
        - pkgs:
            - build-essential
            - python
            - python-dev
            - python-setuptools
            - python-pip
            - python-numpy
            - python-opencv
            - libjpeg-dev
            - libfreetype6-dev
            - zlib1g-dev
            - libwebp-dev
            - liblcms1-dev
            - nginx-light
            - supervisor
            - varnish

# Requirements and their versions:
{% set pip_pkgs = {'Pillow': '2.1.0', 'tornado': '3.1', 'coverage': '3.6', 'pep8': '1.4.6', 'pyflakes': '0.7.3'} %}

{% for pkg_name, pkg_version in pip_pkgs.items() %}
'{{ pkg_name }}':
    pip.installed:
        - name: '{{pkg_name}} == {{pkg_version}}'
{% endfor %}

'/etc/init.d/pilbox':
    file.managed:
        - source: 'salt://files/etc/init.d/pilbox'
        - user: 'root'
        - group: 'root'
        - mode: 755
        - require:
            - pkg: 'deb_pkgs'
            {% for pip_pkg_name in pip_pkgs %}
            - pip: {{ pip_pkg_name }}
            {% endfor %}

'pilbox':
    service.running:
        - enable: True
        - watch:
            - file: '/etc/init.d/pilbox'

'/var/log/supervisor':
    file.directory:
        - user: 'root'
        - group: 'root'
        - mode: 755
        - require:
            - pkg: 'deb_pkgs'

'/etc/default/varnish':
    file.managed:
        - source: 'salt://files/etc/default/varnish'
        - user: 'root'
        - group: 'root'
        - mode: 644
        - require:
            - pkg: 'deb_pkgs'

'/etc/varnish/default.vcl':
    file.managed:
        - source: 'salt://files/etc/varnish/default.vcl'
        - user: 'root'
        - group: 'root'
        - mode: 644
        - require:
            - pkg: 'deb_pkgs'

'/usr/local/bin/varnish.sh':
    file.managed:
        - source: 'salt://files/usr/local/bin/varnish.sh'
        - user: 'root'
        - group: 'root'
        - mode: 755
        - require:
            - pkg: 'deb_pkgs'

'/etc/nginx/nginx.conf':
    file.managed:
        - source: 'salt://files/etc/nginx/nginx.conf'
        - user: 'root'
        - group: 'root'
        - mode: 644
        - require:
            - pkg: 'deb_pkgs'

'/etc/supervisor/conf.d/supervisord.conf':
    file.managed:
        - source: 'salt://files/etc/supervisor/conf.d/supervisord.conf'
        - user: 'root'
        - group: 'root'
        - mode: 644
        - require:
            - pkg: 'deb_pkgs'

'nginx':
    service.running:
        - enable: True
        - watch:
            - file: '/etc/nginx/nginx.conf'

