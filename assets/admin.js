(function(){
  'use strict';

  function slugFor(title){
    var map={
      'Goa Reset / YouTube':'youtube',
      'Telegram Publisher':'telegram',
      'VK Publisher':'vk',
      'Odnoklassniki Publisher':'ok',
      'Inbox':'inbox'
    };
    return map[title] || title.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');
  }

  function iconFor(slug){
    var map={
      youtube:'dashicons-video-alt3',
      telegram:'dashicons-format-chat',
      vk:'dashicons-share',
      ok:'dashicons-groups',
      inbox:'dashicons-email-alt'
    };
    return map[slug] || 'dashicons-admin-generic';
  }

  function enhance(){
    var root=document.querySelector('.wrap.grec-shell');
    if(!root || root.dataset.grecEnhanced==='1') return;
    root.dataset.grecEnhanced='1';

    var headings=Array.prototype.filter.call(root.children,function(node){
      return node.tagName==='H2';
    });
    if(!headings.length) return;

    var sections=[];
    headings.forEach(function(heading,index){
      if(!heading.parentNode || heading.parentNode!==root) return;
      var title=heading.textContent.trim();
      var slug=slugFor(title);
      var section=document.createElement('section');
      section.className='grec-section';
      section.id='grec-'+slug;
      section.dataset.label=title.replace(' Publisher','').replace('Goa Reset / ','');
      root.insertBefore(section,heading);

      var stop=headings[index+1] || null;
      var node=heading;
      while(node && node!==stop){
        var next=node.nextSibling;
        section.appendChild(node);
        node=next;
      }
      sections.push(section);
    });

    root.querySelectorAll(':scope > hr').forEach(function(hr){hr.remove();});

    var nav=document.createElement('nav');
    nav.className='grec-section-nav';
    nav.setAttribute('aria-label','Engagement sections');

    sections.forEach(function(section){
      var slug=section.id.replace('grec-','');
      var link=document.createElement('a');
      link.href='#'+section.id;
      link.dataset.target=section.id;
      link.innerHTML='<span class="dashicons '+iconFor(slug)+'" aria-hidden="true"></span><span>'+section.dataset.label+'</span>';
      nav.appendChild(link);
    });

    var overview=root.querySelector('.grec-status-grid');
    if(overview){
      overview.insertAdjacentElement('afterend',nav);
    }else{
      root.insertBefore(nav,sections[0]);
    }

    nav.addEventListener('click',function(event){
      var link=event.target.closest('a[data-target]');
      if(!link) return;
      var target=document.getElementById(link.dataset.target);
      if(!target) return;
      event.preventDefault();
      target.scrollIntoView({behavior:'smooth',block:'start'});
      history.replaceState(null,'','#'+target.id);
    });

    if('IntersectionObserver' in window){
      var observer=new IntersectionObserver(function(entries){
        var visible=entries
          .filter(function(entry){return entry.isIntersecting;})
          .sort(function(a,b){return b.intersectionRatio-a.intersectionRatio;})[0];
        if(!visible) return;
        nav.querySelectorAll('a').forEach(function(link){
          link.classList.toggle('is-active',link.dataset.target===visible.target.id);
        });
      },{rootMargin:'-20% 0px -60% 0px',threshold:[0,.1,.25,.5]});
      sections.forEach(function(section){observer.observe(section);});
    }

    var hash=window.location.hash;
    if(hash && root.querySelector(hash)){
      window.setTimeout(function(){
        root.querySelector(hash).scrollIntoView({block:'start'});
      },60);
    }
  }

  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded',enhance);
  }else{
    enhance();
  }
})();