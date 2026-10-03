function esc(s) {
    if (s == null) return "";
    return String(s)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;")
        .replace(/`/g, "&#96;");
}

function el(tag, attrs, children) {
    const element = document.createElement(tag);
    if (attrs) {
        for (const [key, value] of Object.entries(attrs)) {
            if (key === 'className') {
                element.className = value;
            } else if (key.startsWith('on') && typeof value === 'function') {
                element.addEventListener(key.slice(2).toLowerCase(), value);
            } else if (key === 'dataset') {
                for (const [dataKey, dataValue] of Object.entries(value)) {
                    element.dataset[dataKey] = dataValue;
                }
            } else if (key === 'style') {
                if (typeof value === 'object') {
                    for (const [styleKey, styleValue] of Object.entries(value)) {
                        element.style[styleKey] = styleValue;
                    }
                } else {
                    element.style.cssText = value;
                }
            } else if (key === 'textContent') {
                element.textContent = value;
            } else if (key === 'innerHTML') {
                // Warning: Only use with trusted/escaped content
                element.innerHTML = value;
            } else {
                element.setAttribute(key, value);
            }
        }
    }
    if (children) {
        if (!Array.isArray(children)) {
            children = [children];
        }
        for (const child of children) {
            if (child == null) continue;
            if (child instanceof Node) {
                element.appendChild(child);
            } else {
                element.appendChild(document.createTextNode(String(child)));
            }
        }
    }
    return element;
}
