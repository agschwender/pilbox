Exec {
  path => [ "/usr/local/bin", "/usr/bin", "/bin" ]
}

node default {
  exec { "apt-update": command => "apt-get update" }
  Exec["apt-update"] -> Package <| |>

  include python
  include python::pil

  python::pip { "tornado":
    ensure => installed,
    require => Class[ "python" ],
  }

  include supervisor
  supervisor::service { "pilbox":
    command => "/var/www/pilbox/app.py",
    require => [ Python::Pip[ "tornado" ], Class[ "python::pil" ] ],
  }

  package { "varnish": ensure => installed }
  package { "nginx": ensure => installed }
}
