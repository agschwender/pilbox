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
    directory => "/var/www",
    command => "python -m pilbox.app",
    require => [ Python::Pip[ "tornado" ], Class[ "python::pil" ] ],
  }

  class { "varnish" : }
  class { "nginx": }
}
