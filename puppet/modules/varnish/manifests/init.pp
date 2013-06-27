class varnish (
      $port = 80,
      $ttl = "1d",
      $app_port = 8888,
      $webserver_port = 8080
      ) {

  package { "varnish": ensure => installed }

  file { "/etc/varnish/default.vcl":
    ensure => present,
    owner => "root",
    group => "root",
    mode => 0644,
    content => template("varnish/etc/varnish/default.vcl.erb"),
    require => Package[ "varnish" ],
    notify => Service[ "varnish" ],
  }

  file { "/etc/default/varnish":
    ensure => present,
    owner => "root",
    group => "root",
    mode => 0644,
    content => template("varnish/etc/default/varnish.erb"),
    require => Package[ "varnish" ],
    notify => Service[ "varnish" ],
  }

  service { "varnish":
    ensure => running,
    enable => true,
    hasrestart => false,
    require => [ Package[ "varnish" ],
                 File[ "/etc/varnish/default.vcl" ],
                 File[ "/etc/default/varnish" ]
                 ]
  }
}
