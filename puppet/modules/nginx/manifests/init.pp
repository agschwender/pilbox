class nginx ( $port = 8080, $app_port = 8888 ) {

  package { "nginx": ensure => installed }

  file { "/etc/nginx/nginx.conf":
    ensure => present,
    owner => "root",
    group => "root",
    mode => 0755,
    source => "puppet:///modules/nginx/etc/nginx/nginx.conf",
    require => Package[ "nginx" ],
    notify => Service[ "nginx" ],
  }

  file { "/etc/nginx/sites-available/pilbox":
    ensure => present,
    owner => "root",
    group => "root",
    mode => 0755,
    content => template("nginx/etc/nginx/sites-available/pilbox.erb"),
    require => Package[ "nginx" ],
    notify => Service[ "nginx" ],
  }

  file { "/etc/nginx/sites-enabled/pilbox":
    ensure => "link",
    target => "/etc/nginx/sites-available/pilbox",
    require => [ Package[ "nginx" ],
                 File[ "/etc/nginx/sites-available/pilbox" ]
                 ],
    notify => Service[ "nginx" ],
  }

  file { "/etc/nginx/sites-enabled/default":
    ensure => absent,
    require => [ Package[ "nginx" ],
                 File[ "/etc/nginx/sites-enabled/pilbox" ] ],
    notify => Service[ "nginx" ],
  }

  service { "nginx":
    ensure => running,
    enable => true,
    hasrestart => true,
    require => Package[ "nginx" ],
  }
}
