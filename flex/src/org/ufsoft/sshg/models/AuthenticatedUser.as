/**
 * @author vampas
 */
package org.ufsoft.sshg.models {

  public class AuthenticatedUser {
    public static var ALIAS : String='org.ufsoft.sshg.models.AuthenticatedUser';
    public var username   : String;
    public var password   : String;
    public var locale     : String;

    public function AuthenticatedUser(
      username : String,
      password : String,
      locale: String)
    {
      this.username  = username;
      this.password  = password;
      this.locale    = locale;
    }
  }
}


