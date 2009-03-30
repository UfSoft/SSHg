/**
 * @author vampas
 */
package org.ufsoft.sshg.events {

  import flash.events.Event;

  public class TranslationEvent extends Event {
    public static const LOAD    :String = "LoadTranslation";
    public static const LOADED  :String = "LoadedTranslation";
    public static const PARSE   :String = "ParseTranslation";
    public static const FAILURE :String = "TranslationFailure";

    public var locale       :String;
    public var translations : Array;

    public function TranslationEvent (
      type          : String,
      locale        : String = null,
      translations  : Array = null,
      bubbles       : Boolean = true,
      cancelable    : Boolean = false
      )
    {
      super(type, bubbles, cancelable);
      this.locale = locale;
      this.translations = translations;
    }

    override public function clone():Event {
      return new TranslationEvent( type, locale, translations, bubbles, cancelable );
    }
  }
}

