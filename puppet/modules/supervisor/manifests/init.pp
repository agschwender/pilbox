class supervisor {
  include supervisor::update

  package { "supervisor": ensure => installed }

  file { "/etc/supervisor":
    ensure => directory,
    purge => true,
    require => Package[ "supervisor" ],
  }

  file { "/etc/supervisor/conf.d":
    ensure => directory,
    purge => true,
    require => File[ "/etc/supervisor" ],
  }

  file { [ "/var/log/supervisor", "/var/run/supervisor" ]:
    ensure => directory,
    purge => true,
    backup => false,
    require => Package[ "supervisor" ],
  }

  file { "/etc/supervisor/supervisord.conf":
    ensure => file,
    source => "puppet:///modules/supervisor/supervisord.conf",
    require => File[ "/etc/supervisor" ],
    notify => Service[ "supervisor" ],
  }

  service { "supervisor":
    ensure => running,
    enable => true,
    hasrestart => false,
    require => [ Package[ "supervisor" ],
                 File[ "/etc/supervisor/supervisord.conf" ]
                 ]
  }
}
