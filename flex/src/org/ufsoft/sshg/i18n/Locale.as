/**
 * @author vampas
 */
package org.ufsoft.sshg.i18n {

  import flash.events.Event;
  import flash.events.EventDispatcher;
  import mx.core.Application;
  import mx.resources.ResourceManager;
  import mx.resources.ResourceBundle;
  import mx.rpc.AbstractOperation;
  import mx.rpc.events.ResultEvent;

  import net.zengrong.logging.Firebug;
  import org.ufsoft.sshg.events.TranslationEvent;

  public class Locale extends EventDispatcher {
    private var rb    : ResourceBundle;
    public var _locale: String;
    public var bundle : String = "sshg";
    private var loaded: Boolean = false;

    private static var singleton:Locale;

    public function Locale(caller:Function = null) {
      super();
      if(caller != Locale.getInstance) {
        throw new Error("Singleton is a singleton class, use Locale.getInstance() instead");
      }
      addEventListener(TranslationEvent.LOAD, backgroundLoad);
      addEventListener(TranslationEvent.PARSE, parseTranslation);
      addEventListener(TranslationEvent.LOADED, translationLoaded);
    }

    public static function getInstance():Locale {
      if (Locale.singleton == null) {
        Locale.singleton = new Locale(arguments.callee);
      }
      return Locale.singleton;
    }

    public function load(locale:String):void {
      this.loaded = false;
      Firebug.debug("Loading locale " + locale);
      this._locale = locale;
      dispatchEvent(new TranslationEvent(TranslationEvent.LOAD, locale));
    }

    private function backgroundLoad(event:TranslationEvent):void {
      if ( ! ResourceManager.getInstance().getResourceBundle(event.locale, this.bundle ) ) {
        var operation : AbstractOperation=Application.application.getOperation(
          'locales.get_translations',
          loadComplete);
        operation.send(event.locale);
      } else {
        dispatchEvent(new TranslationEvent(
          TranslationEvent.LOADED, event.locale, event.translations));
      }
    }

    public function loadComplete(event:ResultEvent):void {
      dispatchEvent(new TranslationEvent(
        TranslationEvent.PARSE, getLocale(), event.result as Array));
    }

    private function parseTranslation(event:TranslationEvent):void {
      Firebug.debug("Parsing locale " + event.locale);
      rb = new ResourceBundle(event.locale, this.bundle);
      for each (var item:Object in event.translations ) {
        //trace(item);
        //Firebug.debug(item);
        rb.content[item.msgid] = item.msgstr;
      }
      ResourceManager.getInstance().addResourceBundle(rb);
      Firebug.debug("Loaded locale " + getLocale());
      dispatchEvent(new TranslationEvent(
        TranslationEvent.LOADED, event.locale, event.translations));
    }

    private function translationLoaded(event:TranslationEvent):void {
      ResourceManager.getInstance().localeChain = [event.locale, 'en_US'];
      this.loaded = true;
      ResourceManager.getInstance().update();
      Firebug.debug("Loaded locale " + getLocale());
    }

    public function getLocale():String {
      return this._locale;
    }
  }
}


