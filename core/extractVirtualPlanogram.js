function extractVirtualPlanogram(config) {
  // find all product tiles
  var containers = document.querySelectorAll(config.productContainer);
  var maxResults = config.max_results || 20;
  // map all private label brands given in config to lowercase
  var privateLabelBrands = (config.private_label_brands || []).map(function(b) {
    return b.toLowerCase();
  });
  // config.fields gives selectors to retrieve each item
  var fields = config.fields || {};
  var metadataSelectors = fields.metadata || [];
  var results = [];
  var limit = Math.min(containers.length, maxResults);

  function getText(el, selector) {
    if (!selector) return "";
    var found = el.querySelector(selector);
    return found ? found.innerText.replace(/\s+/g, " ").trim() : "";
  }

  // for each product tile
  for (var i = 0; i < limit; i++) {
    var tile = containers[i];

    var title = getText(tile, fields.title);
    var price = getText(tile, fields.price);

    var brand = getText(tile, fields.brand);
    if (!brand && title) {
      if (title.indexOf(" - ") !== -1) brand = title.split(" - ")[0].trim();
      else if (title.indexOf(",") !== -1) brand = title.split(",")[0].trim();
    }

    var isSponsored = false;
    if (config.sponsored_selector) {
      isSponsored = tile.querySelector(config.sponsored_selector) !== null;
    }
    if (!isSponsored) {
      var fallback = (config.sponsored_text_fallback || "sponsored").toLowerCase();
      isSponsored = (tile.innerText || "").toLowerCase().indexOf(fallback) !== -1;
    }

    // if no brand selector, check title for private label substring; otherwise exact-match brand
    var isPrivateLabel;
    if (!fields.brand) {
      var titleLower = title.toLowerCase();
      isPrivateLabel = false;
      for (var p = 0; p < privateLabelBrands.length; p++) {
        if (titleLower.indexOf(privateLabelBrands[p]) !== -1) { isPrivateLabel = true; break; }
      }
    } else {
      isPrivateLabel = brand
        ? privateLabelBrands.indexOf(brand.toLowerCase()) !== -1
        : false;
    }

    var badges = "";
    if (config.badge_selector) {
      var badgeEls = tile.querySelectorAll(config.badge_selector);
      var badgeTexts = [];
      for (var b = 0; b < badgeEls.length; b++) {
        var bt = badgeEls[b].innerText.replace(/\s+/g, " ").trim();
        if (bt) badgeTexts.push(bt);
      }
      badges = badgeTexts.join("; ");
    }

    var metadata = [];
    for (var m = 0; m < metadataSelectors.length; m++) {
      var ms = metadataSelectors[m];
      var metaEl = tile.querySelector(ms.selector);
      if (metaEl) {
        metadata.push({ label: ms.label || "", value: metaEl.innerText.replace(/\s+/g, " ").trim() });
      }
    }

    // need to scroll to the bottom for product tiles that haven't loaded yet
    var rect = tile.getBoundingClientRect();
    var boundingBox = {
      x: Math.round(rect.left + document.documentElement.scrollLeft),
      y: Math.round(rect.top + document.documentElement.scrollTop),
      width: Math.round(rect.width),
      height: Math.round(rect.height)
    };

    results.push({
      index: i + 1,
      title: title,
      price: price,
      brand: brand,
      is_sponsored: isSponsored,
      is_private_label: isPrivateLabel,
      badges: badges,
      metadata: metadata,
      boundingBox: boundingBox,
      tile_x: boundingBox.x,
      tile_y: boundingBox.y,
      domOrder: i,
      timestamp: new Date().toISOString(),
      url: document.location.href
    });
  }

  // sort by x, y visual position
  results.sort(function(a, b) {
    if (a.boundingBox.y !== b.boundingBox.y) return a.boundingBox.y - b.boundingBox.y;
    return a.boundingBox.x - b.boundingBox.x;
  });

  for (var r = 0; r < results.length; r++) results[r].index = r + 1;

  return results;
}
