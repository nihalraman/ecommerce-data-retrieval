(function() {
  var now = new Date();
  var SERVER_URL = 'http://localhost:8585/capture';

  // --- Category auto-detection from URL search params ---
  var CATEGORY_PARAMS = {
    'amazon': 'k',
    'walmart': 'q',
    'target': 'searchTerm',
    'costco': 'keyword',
    '1688': 'keywords'
  };

  function detectCategory() {
    var hostname = document.location.hostname.toLowerCase();
    var params = new URLSearchParams(document.location.search);
    for (var site in CATEGORY_PARAMS) {
      if (CATEGORY_PARAMS.hasOwnProperty(site) && hostname.indexOf(site) !== -1) {
        var val = params.get(CATEGORY_PARAMS[site]);
        if (val) return val.replace(/\+/g, ' ');
      }
    }
    return '';
  }

  var autoCategory = detectCategory();
  var category = prompt('Confirm product category:', autoCategory);
  if (category === null) { return; }

  var includeScreenshot = confirm('Include screenshot? (slower — adds ~10s)');


  // --- Clone DOM and strip unnecessary elements (same as capture.js) ---
  var clone = document.documentElement.cloneNode(true);

  var scripts = clone.querySelectorAll('script, noscript');
  for (var i = scripts.length - 1; i >= 0; i--) {
    scripts[i].parentNode.removeChild(scripts[i]);
  }

  var walker = document.createTreeWalker(clone, NodeFilter.SHOW_COMMENT, null, false);
  var comments = [];
  while (walker.nextNode()) { comments.push(walker.currentNode); }
  for (var i = 0; i < comments.length; i++) {
    comments[i].parentNode.removeChild(comments[i]);
  }

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

  var iframes = clone.querySelectorAll('iframe');
  for (var i = iframes.length - 1; i >= 0; i--) {
    var ifr = iframes[i];
    var w = ifr.getAttribute('width');
    var h = ifr.getAttribute('height');
    if (w === '0' || w === '1' || h === '0' || h === '1') {
      ifr.parentNode.removeChild(ifr);
    }
  }

  var links = clone.querySelectorAll('link[rel="preload"], link[rel="prefetch"], link[rel="dns-prefetch"]');
  for (var i = links.length - 1; i >= 0; i--) {
    links[i].parentNode.removeChild(links[i]);
  }

  var htmlContent = clone.outerHTML;
  var metadata = {
    url: document.location.href,
    title: document.title,
    timestamp: now.toISOString(),
    viewport: { width: window.innerWidth, height: window.innerHeight },
    scrollHeight: document.documentElement.scrollHeight,
    scrollY: window.scrollY
  };

  // --- Show status banner ---
  var banner = document.createElement('div');
  banner.textContent = includeScreenshot ? 'Capturing screenshot...' : 'Capturing page...';
  banner.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:2147483647;' +
    'background:#3b82f6;color:#fff;text-align:center;padding:12px;font:bold 16px sans-serif;';
  document.body.appendChild(banner);

  // --- Helper: send payload to server ---
  function sendToServer(screenshotB64) {
    banner.textContent = 'Uploading to server...';
    banner.style.background = '#3b82f6';

    var payload = JSON.stringify({
      url: metadata.url,
      title: metadata.title,
      timestamp: metadata.timestamp,
      viewport: metadata.viewport,
      scrollHeight: metadata.scrollHeight,
      scrollY: metadata.scrollY,
      html: htmlContent,
      screenshot_b64: screenshotB64,
      category: category
    });

    var xhr = new XMLHttpRequest();
    xhr.open('POST', SERVER_URL, true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.onload = function() {
      var parsed = {};
      try { parsed = JSON.parse(xhr.responseText); } catch(e) {}
      if (xhr.status === 200 && parsed.success) {
        showBanner(true, 'Captured! ' + (parsed.products_found || 0) + ' products uploaded to Dropbox');
      } else {
        showBanner(false, 'Upload failed: ' + (parsed.error || 'Unknown error'));
      }
    };
    xhr.onerror = function() {
      // Server unreachable — fall back to local file download
      fallbackDownload();
    };
    xhr.send(payload);
  }

  // --- Helper: show result banner ---
  function showBanner(success, message) {
    banner.textContent = message;
    banner.style.background = success ? '#22c55e' : '#ef4444';
    setTimeout(function() {
      try { document.body.removeChild(banner); } catch(e) {}
    }, 5000);
  }

  // --- Helper: fallback to local file download if server is unreachable ---
  function fallbackDownload() {
    var pad = function(n) { return n < 10 ? '0' + n : '' + n; };
    var stamp = now.getFullYear() +
      pad(now.getMonth() + 1) + pad(now.getDate()) + '_' +
      pad(now.getHours()) + pad(now.getMinutes()) + pad(now.getSeconds());
    var filename = 'capture_' + document.location.hostname + '_' + stamp + '.json';

    var data = {};
    for (var key in metadata) {
      if (metadata.hasOwnProperty(key)) data[key] = metadata[key];
    }
    data.html = htmlContent;

    var blob = new Blob([JSON.stringify(data)], { type: 'application/json' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);

    banner.textContent = 'Server unavailable - file saved locally: ' + filename;
    banner.style.background = '#eab308';
    setTimeout(function() {
      try { document.body.removeChild(banner); } catch(e) {}
    }, 5000);
  }

  // --- Capture screenshot (if requested) and send ---
  if (!includeScreenshot) {
    sendToServer('');
  } else {
    var script = document.createElement('script');
    script.src = 'https://html2canvas.hertzen.com/dist/html2canvas.min.js';
    script.onload = function() {
      html2canvas(document.body, { useCORS: true, logging: false }).then(function(canvas) {
        var screenshotB64 = canvas.toDataURL('image/jpeg', 0.7).split(',')[1];
        sendToServer(screenshotB64);
      })['catch'](function() {
        // Screenshot failed, proceed without it
        sendToServer('');
      });
    };
    script.onerror = function() {
      // CDN unreachable, proceed without screenshot
      sendToServer('');
    };
    document.head.appendChild(script);
  }

  void(0);
})()
