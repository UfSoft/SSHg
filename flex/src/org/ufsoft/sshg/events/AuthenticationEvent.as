/**
 * @author vampas
 */
package org.ufsoft.sshg.events {
  import flash.events.Event;
  import org.ufsoft.sshg.models.AuthenticatedUser;

  public class AuthenticationEvent extends Event {
    public static const SEND    :String = "SendAuthentication";
    public static const NEEDED  :String = "NeedAuthentication";
    public static const SUCESS  :String = "AuthenticationSucessful";
    public static const FAILURE :String = "AuthenticationFailure";
    public var user             :AuthenticatedUser;

    public function AuthenticationEvent(
      type      :String,
      user      :AuthenticatedUser=null,
      bubbles   :Boolean = true,
      cancelable:Boolean = false
      )
    {
      super(type, bubbles, cancelable);
      this.user = user;
    }

    override public function clone():Event {
      return new AuthenticationEvent( type, user, bubbles, cancelable );
    }
  }
}


