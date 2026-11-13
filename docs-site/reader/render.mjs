import MarkdownIt from 'markdown-it';
import Prism from 'prismjs';
import 'prismjs/components/prism-python.js';
import 'prismjs/components/prism-yaml.js';
import 'prismjs/components/prism-bash.js';
import 'prismjs/components/prism-json.js';
import {createHash} from 'node:crypto';
import {content} from './settings.mjs';
import {slug,headingIdentities,anchorPattern,plainHeading} from './headings.mjs';
export {content};
export const hash=value=>createHash('sha256').update(value).digest('hex');
export const escape=value=>String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
export const pageLabel=page=>page.navigationTitle||page.title;
function documentText(markdown,{omitPreamble=false}={}){
  const tokens=new MarkdownIt({html:true}).parse(markdown,{}),lines=markdown.split('\n');
  const at=tokens.findIndex(token=>token.type==='heading_open'&&token.tag==='h1');
  const removed=[];if(at>=0){removed.push(tokens[at].map);const before=tokens[at-1]?.type==='html_block'?tokens[at-1]:tokens[at-1]?.type==='paragraph_close'?tokens[at-2]:null;if(before&&anchorPattern.test(before.content.trim()))removed.push(before.map);if(omitPreamble)removed.push([0,tokens[at].map[0]]);}
  let first=at>=0?at+3:0;
  while(true){if(tokens[first]?.type==='html_block'&&(tokens[first].content.trim().startsWith('<!--')||anchorPattern.test(tokens[first].content.trim()))){first++;continue;}if(tokens[first]?.type==='paragraph_open'&&anchorPattern.test(tokens[first+1]?.content.trim()||'')){first+=3;continue;}break;}
  if(tokens[first]?.type==='blockquote_open')first++;
  const paragraph=tokens[first]?.type==='paragraph_open'?tokens[first]:null;
  const inline=paragraph?tokens[first+1]:null;
  const introduction=inline?.children?.map(token=>['text','code_inline','image'].includes(token.type)?token.content:['softbreak','hardbreak'].includes(token.type)?' ':'').join('')||'';
  if(paragraph)removed.push(paragraph.map);
  const kept=lines.map((_,line)=>line).filter(line=>!removed.some(range=>range&&line>=range[0]&&line<range[1]));
  return {body:kept.map(line=>lines[line]).join('\n'),kept,introduction,introductionSource:inline?.content||''};
}
function renderMarkdown(page,pages,revision){
  const md=new MarkdownIt({html:true,linkify:false,typographer:false});const headings=[],seen=new Map();let codeCount=0,linkCount=0,identities=new Map();
  md.core.ruler.push('reader_heading_identities',state=>{identities=headingIdentities(state.tokens);});
  const htmlBlock=md.renderer.rules.html_block;
  md.renderer.rules.html_block=(tokens,index,options,env,renderer)=>{
    if(anchorPattern.test(tokens[index].content.trim()))return '';
    return htmlBlock(tokens,index,options,env,renderer);
  };
  md.renderer.rules.heading_open=(tokens,index,options,env,renderer)=>{const token=tokens[index],text=plainHeading(tokens[index+1]);const identity=identities.get(index),id=identity.id;token.attrSet('id',id);if(identity.explicit)token.attrSet('data-heading-interface',identity.kind);token.attrSet('tabindex','-1');if(token.tag==='h2')headings.push({title:text,id});return renderer.renderToken(tokens,index,options);};
  md.renderer.rules.paragraph_open=(tokens,index,options,env,renderer)=>{const text=tokens[index+1]?.content||'';if(anchorPattern.test(text.trim())){tokens[index+1].children=[];return '';}const id=`p-${hash(text).slice(0,12)}`;const count=seen.get(id)||0;seen.set(id,count+1);tokens[index].attrSet('id',count?`${id}-${count}`:id);tokens[index].attrSet('data-passage','');return renderer.renderToken(tokens,index,options);};
  md.renderer.rules.paragraph_close=(tokens,index,options,env,renderer)=>anchorPattern.test(tokens[index-1]?.content?.trim()||'')?'':renderer.renderToken(tokens,index,options);
  const originalLink=md.renderer.rules.link_open||((tokens,index,options,env,renderer)=>renderer.renderToken(tokens,index,options));
  md.renderer.rules.link_open=(tokens,index,options,env,renderer)=>{
    const token=tokens[index],href=token.attrGet('href');
    const repository=content.product.repository,sourcePrefix=repository+'/blob/main/';
    const repositoryLink=href.startsWith(sourcePrefix);
    const authoredSource=repositoryLink?href.slice(sourcePrefix.length):href;
    if(repositoryLink||!/^(?:[a-z][a-z0-9+.-]*:|\/|#)/i.test(href)){
      const base='https://source.invalid/'+(repositoryLink?'':page.source);
      const url=new URL(authoredSource,base);
      const resolved=decodeURIComponent(url.pathname.slice(1));
      const target=pages.find(candidate=>candidate.source===resolved);
      if(target){
        token.attrSet('href',target.url+url.search+url.hash);
        token.attrSet('id','link-'+hash(page.source+':'+href+':'+linkCount++).slice(0,12));
        if(target.part==='Reference')token.attrSet('data-reference','');
      }else if(!repositoryLink){
        token.attrSet('href',repository+'/blob/'+revision+'/'+url.pathname.slice(1)+url.search+url.hash);
      }
    }
    return originalLink(tokens,index,options,env,renderer);
  };
  md.renderer.rules.fence=(tokens,index)=>{const token=tokens[index],language=token.info.trim().split(/\s+/)[0]||'text',source=token.content;const id=`code-${++codeCount}`;const grammar=Prism.languages[language==='python-fragment'?'python':language==='sh'?'bash':language];
    const renderedLines=[''];
    function append(value,classes=[]){
      if(typeof value==='string'){const parts=value.split('\n');for(let n=0;n<parts.length;n++){if(n)renderedLines.push('');const text=escape(parts[n]);renderedLines[renderedLines.length-1]+=classes.length?`<span class="token ${classes.map(escape).join(' ')}">${text}</span>`:text;}}
      else if(Array.isArray(value))value.forEach(token=>append(token,classes));
      else append(value.content,[...classes,value.type]);
    }
    append(grammar?Prism.tokenize(source.replace(/\n$/,''),grammar):source.replace(/\n$/,''));
    const lines=renderedLines.map((line,i)=>`<span class="code-line" id="${id}-L${i+1}"><a class="line-number" href="#${id}-L${i+1}" aria-hidden="true" tabindex="-1">${i+1}</a><span class="code-src">${line||' '}</span></span>`).join('');
    return `<figure class="code" id="${id}" data-source="${Buffer.from(source).toString('base64')}"><figcaption class="code-bar"><span>${escape(language)}</span><span><button type="button" data-wrap aria-pressed="true" hidden>Wrap</button> <button type="button" data-copy hidden>Copy</button></span></figcaption><pre><code>${lines}</code></pre></figure>`;
  };
  const originalTableOpen=md.renderer.rules.table_open||(()=>'<table>');const originalTableClose=md.renderer.rules.table_close||(()=>'</table>');
  md.renderer.rules.table_open=(...args)=>'<div class="table-scroll" tabindex="0" role="region" aria-label="Scrollable reference table">'+originalTableOpen(...args);
  md.renderer.rules.table_close=(...args)=>originalTableClose(...args)+'</div>';
  const {body,introduction,introductionSource}=documentText(page.markdown,page);const introductionHtml=md.renderInline(introductionSource);return {html:md.render(body),headings,introduction,introductionHtml};
}
export function renderPage(page,pages,revision){
  const {html,headings,introduction,introductionHtml}=renderMarkdown(page,pages,revision);const book=pages.filter(p=>p.bookOrder!==undefined).sort((a,b)=>a.bookOrder-b.bookOrder);const at=book.indexOf(page),next=at>=0?book[at+1]:null,previous=at>0?book[at-1]:null;
  const home=book[0];const reference=pages.find(p=>p.route==='/reference/'),developer=pages.find(p=>p.source==='docs/Developer/README.md');
  const navigation=page.part==='Book'?book:pages.filter(p=>p.part===page.part&&p.source&&p.listed!==false).sort((a,b)=>pageLabel(a).localeCompare(pageLabel(b)));
  const item=p=>`<li><a href="${p.url}"${p===page?' aria-current="page"':''}>${escape(pageLabel(p))}</a></li>`;
  const groups=new Map();for(const entry of navigation){const group=entry.navigationGroup||page.part;if(!groups.has(group))groups.set(group,[]);groups.get(group).push(entry);}
  const nav=page.part==='Book'?navigation.map(item).join('')+pages.filter(p=>p.part==='Book'&&p.bookOrder===undefined&&p.source).map(item).join(''):[...groups].map(([group,entries])=>`<li class="nav-group"><details${entries.includes(page)?' open':''}><summary>${escape(group)}</summary><ul>${entries.map(item).join('')}</ul></details></li>`).join('');
  const contents=headings.map(h=>`<li><a href="#${escape(h.id)}">${escape(h.title)}</a></li>`).join('');
  const mobile=`<details class="mobile-nav"><summary>Contents</summary><nav aria-label="Chapter navigation"><p class="label">${page.part==='Book'?'The book':escape(page.part)}</p><ul>${nav}</ul></nav><nav aria-label="In this chapter"><p class="label">In this chapter</p><ol>${contents}</ol></nav></details>`;
  const firstParagraph=introduction||page.title;
  const provenance=page.preamble?`<details><summary>Source evidence</summary><pre>${escape(page.preamble)}</pre></details>`:'';
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escape(page.title)} — ${escape(content.product.name)}</title><meta name="description" content="${escape(firstParagraph)}"><link rel="canonical" href="${content.product.origin}${page.url}"><style>@view-transition{navigation:auto}@media(prefers-reduced-motion:reduce){@view-transition{navigation:none}}</style><link rel="stylesheet" href="${content.product.basePath}/assets/book.css"><script type="module" src="${content.product.basePath}/assets/main.mjs"></script></head><body data-part="${escape(page.part)}" data-product="${escape(content.product.id)}" data-content="${escape(page.source||'index:'+page.part)}" data-interface="both" data-search="${content.product.basePath}/search.json"><a class="skip" href="#main">Skip to the chapter</a><header class="site-header"><div class="header-inner"><a class="wordmark" href="${home.url}">${escape(content.product.wordmark)}</a><nav class="part-nav" aria-label="Parts"><a href="${home.url}"${page.part==='Book'?' aria-current="true"':''}>Book</a><a href="${reference.url}"${page.part==='Reference'?' aria-current="true"':''}>Reference</a><a href="${developer.url}"${page.part==='Developer'?' aria-current="true"':''}>Developer</a><button type="button" data-search-open hidden>Search</button></nav></div><div class="reading-progress"></div></header><div class="hero"><div class="hero-inner"><p class="label">${escape(page.part)} / ${escape(content.product.subject)}</p><h1 id="${escape([...headingIdentities(new MarkdownIt({html:true}).parse(page.markdown,{})).values()][0]?.id||slug(page.title))}" tabindex="-1">${escape(page.title)}</h1>${introduction?`<p class="hero-lead">${introductionHtml}</p>`:''}</div></div><div class="layout"><aside class="chapter-nav" aria-label="${page.part==='Book'?'Book chapters':escape(page.part)+' navigation'}"><p class="label">${page.part==='Book'?'The book':escape(page.part)}</p><ul>${nav}</ul><nav class="chapter-contents" aria-label="In this chapter"><p class="label">In this chapter</p><ol>${contents}</ol></nav></aside><main id="main" tabindex="-1">${mobile}<article>${html}${provenance}</article><p class="status" data-status role="status" aria-live="polite"></p><div class="page-end"><span>${previous?`Previous<a href="${previous.url}">${escape(previous.title)}</a>`:escape(content.product.name)}</span><span>${next?`Continue<a href="${next.url}">${escape(next.title)}</a>`:`<a href="${home.url}">Return to the book</a>`}</span></div><div class="page-end">${page.source?`<a href="${content.product.repository}/edit/main/${escape(page.source)}">Edit this source</a>`:'Generated from the canonical source map'}<span>Checkout revision · ${escape(revision.slice(0,8))}</span></div></main></div><dialog class="reference-dialog" data-reference-dialog aria-label="Reference"><header class="dialog-head"><span class="label">Reference / keep your place</span><button type="button" data-reference-close>Return to chapter</button></header><div class="return-rule"></div><div class="reference-body" data-reference-body></div></dialog><dialog class="search-dialog" data-search-dialog aria-label="Search ${escape(content.product.name)}"><header class="dialog-head"><span class="label">Find a passage</span><button type="button" data-search-close>Close</button></header><div class="search-body"><label for="search">Search the book and references</label><input id="search" type="search" autocomplete="off"><p data-search-count class="status" aria-live="polite"></p><ol></ol></div></dialog></body></html>`;
}
