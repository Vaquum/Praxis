import {initCode,revealCodeRange} from './code.mjs';
import {initPlace} from './place.mjs';
import {initNavigation} from './navigation.mjs';
import {initSearch} from './search.mjs';
initCode();await document.fonts.ready;initPlace();initNavigation();initSearch();
addEventListener('hashchange',()=>{
  if(!history.state?.readerReference)revealCodeRange(document.querySelector('main article'));
});
