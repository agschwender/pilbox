class supervisor::update {
  exec { "supervisor::update":
    command     => "/usr/bin/supervisorctl update",
    logoutput   => on_failure,
    refreshonly => true,
    require     => Service[ "supervisor" ],
  }
}
