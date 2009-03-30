/**
 * @author vampas
 */
package org.ufsoft.sshg.models {

  public class RepositoryUser {
    public static var ALIAS : String='org.ufsoft.sshg.models.RepositoryUser';
    public var username   : String;
    public var password   : String;
    public var added      : String;
    public var last_login : String;
    public var is_admin   : Boolean;
    public var locked_out : Boolean;

    public function RepositoryUser(
      username  : String,
      password  : String,
      added     : String,
      last_login: String,
      is_admin  : Boolean,
      locked_out: Boolean)
    {
      this.username   = username;
      this.password   = password;
      this.added      = added;
      this.last_login = last_login;
      this.is_admin   = is_admin;
      this.locked_out = locked_out;
    }
  }
}


