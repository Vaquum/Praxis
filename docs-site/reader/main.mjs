import {initCode,revealCodeRange} from './code.mjs';
import {initPlace} from './place.mjs';
import {initNavigation} from './navigation.mjs';
import {initSearch} from './search.mjs';
initCode();await document.fonts.ready;initPlace();initNavigation();initSearch();
addEventListener('hashchange',()=>revealCodeRange());

if(!matchMedia("(prefers-reduced-motion: reduce)").matches)document.querySelector(".hero-inner")?.animate([{transform:"translateY(6px)"},{transform:"none"}],{duration:220,easing:"cubic-bezier(.2,.7,.2,1)"});
