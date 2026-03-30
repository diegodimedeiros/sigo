(function () {
  function getCookie(name) {
    const cookies = document.cookie ? document.cookie.split(';') : [];
    for (let i = 0; i < cookies.length; i += 1) {
      const cookie = cookies[i].trim();
      if (cookie.startsWith(name + '=')) {
        return decodeURIComponent(cookie.slice(name.length + 1));
      }
    }
    return '';
  }

  function getCsrfToken() {
    return getCookie('csrftoken');
  }

  function buildCsrfHeaders(extraHeaders) {
    const headers = Object.assign({}, extraHeaders || {});
    const token = getCsrfToken();
    if (token && !headers['X-CSRFToken']) {
      headers['X-CSRFToken'] = token;
    }
    if (!headers['X-Requested-With']) {
      headers['X-Requested-With'] = 'XMLHttpRequest';
    }
    return headers;
  }

  function csrfFetch(url, options) {
    const requestOptions = Object.assign({ credentials: 'same-origin' }, options || {});
    requestOptions.headers = buildCsrfHeaders(requestOptions.headers);
    return fetch(url, requestOptions);
  }

  window.SigoCsrf = {
    getCookie,
    getCsrfToken,
    buildCsrfHeaders,
    fetch: csrfFetch,
  };
}());
