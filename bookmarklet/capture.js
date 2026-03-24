(function() {
  var now = new Date();
  var pad = function(n) { return n < 10 ? '0' + n : '' + n; };
  var stamp = now.getFullYear() +
    pad(now.getMonth() + 1) + pad(now.getDate()) + '_' +
    pad(now.getHours()) + pad(now.getMinutes()) + pad(now.getSeconds());
  var filename = 'capture_' + document.location.hostname + '_' + stamp + '.json';

  // Clone DOM and strip unnecessary elements to reduce file size
  var clone = document.documentElement.cloneNode(true);

  // Remove script and noscript tags
  var scripts = clone.querySelectorAll('script, noscript');
  for (var i = scripts.length - 1; i >= 0; i--) {
    scripts[i].parentNode.removeChild(scripts[i]);
  }

  // Remove HTML comments
  var walker = document.createTreeWalker(clone, NodeFilter.SHOW_COMMENT, null, false);
  var comments = [];
  while (walker.nextNode()) { comments.push(walker.currentNode); }
  for (var i = 0; i < comments.length; i++) {
    comments[i].parentNode.removeChild(comments[i]);
  }

  // Remove tracking pixels (1x1 or 0x0 images, known tracking domains)
  var imgs = clone.querySelectorAll('img');
  for (var i = imgs.length - 1; i >= 0; i--) {
    var img = imgs[i];
    var w = img.getAttribute('width');
    var h = img.getAttribute('height');
    var src = (img.getAttribute('src') || '').toLowerCase();
    if ((w === '1' || w === '0' || h === '1' || h === '0') ||
        (/pixel|beacon|track|analytics|doubleclick|facebook\.com\/tr/.test(src))) {
      img.parentNode.removeChild(img);
    }
  }

  // Remove tracking iframes (0x0 or 1x1)
  var iframes = clone.querySelectorAll('iframe');
  for (var i = iframes.length - 1; i >= 0; i--) {
    var ifr = iframes[i];
    var w = ifr.getAttribute('width');
    var h = ifr.getAttribute('height');
    if (w === '0' || w === '1' || h === '0' || h === '1') {
      ifr.parentNode.removeChild(ifr);
    }
  }

  // Remove preload/prefetch/dns-prefetch link tags (not needed for re-rendering)
  var links = clone.querySelectorAll('link[rel="preload"], link[rel="prefetch"], link[rel="dns-prefetch"]');
  for (var i = links.length - 1; i >= 0; i--) {
    links[i].parentNode.removeChild(links[i]);
  }

  var data = {
    url: document.location.href,
    title: document.title,
    timestamp: now.toISOString(),
    viewport: { width: window.innerWidth, height: window.innerHeight },
    scrollHeight: document.documentElement.scrollHeight,
    scrollY: window.scrollY,
    html: clone.outerHTML
  };
  var blob = new Blob([JSON.stringify(data)], { type: 'application/json' });
  var a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);

  // Visual confirmation banner
  var banner = document.createElement('div');
  banner.textContent = 'Page captured: ' + filename;
  banner.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:2147483647;' +
    'background:#22c55e;color:#fff;text-align:center;padding:12px;font:bold 16px sans-serif;';
  document.body.appendChild(banner);
  setTimeout(function() { document.body.removeChild(banner); }, 3000);

  void(0);
})()
