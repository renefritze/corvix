var z, y, ke, D, ie, we, Se, Te, ee, X, Q, W = {}, q = [], Fe = /acit|ex(?:s|g|n|p|$)|rph|grid|ows|mnc|ntw|ine[ch]|zoo|^ord|itera/i, V = Array.isArray;
function E(e, t) {
  for (var n in t) e[n] = t[n];
  return e;
}
function te(e) {
  e && e.parentNode && e.parentNode.removeChild(e);
}
function He(e, t, n) {
  var o, l, r, _ = {};
  for (r in t) r == "key" ? o = t[r] : r == "ref" ? l = t[r] : _[r] = t[r];
  if (arguments.length > 2 && (_.children = arguments.length > 3 ? z.call(arguments, 2) : n), typeof e == "function" && e.defaultProps != null) for (r in e.defaultProps) _[r] === void 0 && (_[r] = e.defaultProps[r]);
  return I(e, _, o, l, null);
}
function I(e, t, n, o, l) {
  var r = { type: e, props: t, key: n, ref: o, __k: null, __: null, __b: 0, __e: null, __c: null, constructor: void 0, __v: l ?? ++ke, __i: -1, __u: 0 };
  return l == null && y.vnode != null && y.vnode(r), r;
}
function G(e) {
  return e.children;
}
function j(e, t) {
  this.props = e, this.context = t;
}
function U(e, t) {
  if (t == null) return e.__ ? U(e.__, e.__i + 1) : null;
  for (var n; t < e.__k.length; t++) if ((n = e.__k[t]) != null && n.__e != null) return n.__e;
  return typeof e.type == "function" ? U(e) : null;
}
function Pe(e) {
  if (e.__P && e.__d) {
    var t = e.__v, n = t.__e, o = [], l = [], r = E({}, t);
    r.__v = t.__v + 1, y.vnode && y.vnode(r), ne(e.__P, r, t, e.__n, e.__P.namespaceURI, 32 & t.__u ? [n] : null, o, n ?? U(t), !!(32 & t.__u), l), r.__v = t.__v, r.__.__k[r.__i] = r, Ee(o, r, l), t.__e = t.__ = null, r.__e != n && Ce(r);
  }
}
function Ce(e) {
  if ((e = e.__) != null && e.__c != null) return e.__e = e.__c.base = null, e.__k.some(function(t) {
    if (t != null && t.__e != null) return e.__e = e.__c.base = t.__e;
  }), Ce(e);
}
function _e(e) {
  (!e.__d && (e.__d = !0) && D.push(e) && !B.__r++ || ie != y.debounceRendering) && ((ie = y.debounceRendering) || we)(B);
}
function B() {
  try {
    for (var e, t = 1; D.length; ) D.length > t && D.sort(Se), e = D.shift(), t = D.length, Pe(e);
  } finally {
    D.length = B.__r = 0;
  }
}
function $e(e, t, n, o, l, r, _, c, u, a, d) {
  var s, h, f, k, T, b, p, m = o && o.__k || q, C = t.length;
  for (u = Me(n, t, m, u, C), s = 0; s < C; s++) (f = n.__k[s]) != null && (h = f.__i != -1 && m[f.__i] || W, f.__i = s, b = ne(e, f, h, l, r, _, c, u, a, d), k = f.__e, f.ref && h.ref != f.ref && (h.ref && re(h.ref, null, f), d.push(f.ref, f.__c || k, f)), T == null && k != null && (T = k), (p = !!(4 & f.__u)) || h.__k === f.__k ? u = xe(f, u, e, p) : typeof f.type == "function" && b !== void 0 ? u = b : k && (u = k.nextSibling), f.__u &= -7);
  return n.__e = T, u;
}
function Me(e, t, n, o, l) {
  var r, _, c, u, a, d = n.length, s = d, h = 0;
  for (e.__k = new Array(l), r = 0; r < l; r++) (_ = t[r]) != null && typeof _ != "boolean" && typeof _ != "function" ? (typeof _ == "string" || typeof _ == "number" || typeof _ == "bigint" || _.constructor == String ? _ = e.__k[r] = I(null, _, null, null, null) : V(_) ? _ = e.__k[r] = I(G, { children: _ }, null, null, null) : _.constructor === void 0 && _.__b > 0 ? _ = e.__k[r] = I(_.type, _.props, _.key, _.ref ? _.ref : null, _.__v) : e.__k[r] = _, u = r + h, _.__ = e, _.__b = e.__b + 1, c = null, (a = _.__i = Le(_, n, u, s)) != -1 && (s--, (c = n[a]) && (c.__u |= 2)), c == null || c.__v == null ? (a == -1 && (l > d ? h-- : l < d && h++), typeof _.type != "function" && (_.__u |= 4)) : a != u && (a == u - 1 ? h-- : a == u + 1 ? h++ : (a > u ? h-- : h++, _.__u |= 4))) : e.__k[r] = null;
  if (s) for (r = 0; r < d; r++) (c = n[r]) != null && (2 & c.__u) == 0 && (c.__e == o && (o = U(c)), De(c, c));
  return o;
}
function xe(e, t, n, o) {
  var l, r;
  if (typeof e.type == "function") {
    for (l = e.__k, r = 0; l && r < l.length; r++) l[r] && (l[r].__ = e, t = xe(l[r], t, n, o));
    return t;
  }
  e.__e != t && (o && (t && e.type && !t.parentNode && (t = U(e)), n.insertBefore(e.__e, t || null)), t = e.__e);
  do
    t = t && t.nextSibling;
  while (t != null && t.nodeType == 8);
  return t;
}
function Le(e, t, n, o) {
  var l, r, _, c = e.key, u = e.type, a = t[n], d = a != null && (2 & a.__u) == 0;
  if (a === null && c == null || d && c == a.key && u == a.type) return n;
  if (o > (d ? 1 : 0)) {
    for (l = n - 1, r = n + 1; l >= 0 || r < t.length; ) if ((a = t[_ = l >= 0 ? l-- : r++]) != null && (2 & a.__u) == 0 && c == a.key && u == a.type) return _;
  }
  return -1;
}
function ae(e, t, n) {
  t[0] == "-" ? e.setProperty(t, n ?? "") : e[t] = n == null ? "" : typeof n != "number" || Fe.test(t) ? n : n + "px";
}
function L(e, t, n, o, l) {
  var r, _;
  e: if (t == "style") if (typeof n == "string") e.style.cssText = n;
  else {
    if (typeof o == "string" && (e.style.cssText = o = ""), o) for (t in o) n && t in n || ae(e.style, t, "");
    if (n) for (t in n) o && n[t] == o[t] || ae(e.style, t, n[t]);
  }
  else if (t[0] == "o" && t[1] == "n") r = t != (t = t.replace(Te, "$1")), _ = t.toLowerCase(), t = _ in e || t == "onFocusOut" || t == "onFocusIn" ? _.slice(2) : t.slice(2), e.l || (e.l = {}), e.l[t + r] = n, n ? o ? n.u = o.u : (n.u = ee, e.addEventListener(t, r ? Q : X, r)) : e.removeEventListener(t, r ? Q : X, r);
  else {
    if (l == "http://www.w3.org/2000/svg") t = t.replace(/xlink(H|:h)/, "h").replace(/sName$/, "s");
    else if (t != "width" && t != "height" && t != "href" && t != "list" && t != "form" && t != "tabIndex" && t != "download" && t != "rowSpan" && t != "colSpan" && t != "role" && t != "popover" && t in e) try {
      e[t] = n ?? "";
      break e;
    } catch {
    }
    typeof n == "function" || (n == null || n === !1 && t[4] != "-" ? e.removeAttribute(t) : e.setAttribute(t, t == "popover" && n == 1 ? "" : n));
  }
}
function ce(e) {
  return function(t) {
    if (this.l) {
      var n = this.l[t.type + e];
      if (t.t == null) t.t = ee++;
      else if (t.t < n.u) return;
      return n(y.event ? y.event(t) : t);
    }
  };
}
function ne(e, t, n, o, l, r, _, c, u, a) {
  var d, s, h, f, k, T, b, p, m, C, $, N, M, R, F, v = t.type;
  if (t.constructor !== void 0) return null;
  128 & n.__u && (u = !!(32 & n.__u), r = [c = t.__e = n.__e]), (d = y.__b) && d(t);
  e: if (typeof v == "function") try {
    if (p = t.props, m = v.prototype && v.prototype.render, C = (d = v.contextType) && o[d.__c], $ = d ? C ? C.props.value : d.__ : o, n.__c ? b = (s = t.__c = n.__c).__ = s.__E : (m ? t.__c = s = new v(p, $) : (t.__c = s = new j(p, $), s.constructor = v, s.render = je), C && C.sub(s), s.state || (s.state = {}), s.__n = o, h = s.__d = !0, s.__h = [], s._sb = []), m && s.__s == null && (s.__s = s.state), m && v.getDerivedStateFromProps != null && (s.__s == s.state && (s.__s = E({}, s.__s)), E(s.__s, v.getDerivedStateFromProps(p, s.__s))), f = s.props, k = s.state, s.__v = t, h) m && v.getDerivedStateFromProps == null && s.componentWillMount != null && s.componentWillMount(), m && s.componentDidMount != null && s.__h.push(s.componentDidMount);
    else {
      if (m && v.getDerivedStateFromProps == null && p !== f && s.componentWillReceiveProps != null && s.componentWillReceiveProps(p, $), t.__v == n.__v || !s.__e && s.shouldComponentUpdate != null && s.shouldComponentUpdate(p, s.__s, $) === !1) {
        t.__v != n.__v && (s.props = p, s.state = s.__s, s.__d = !1), t.__e = n.__e, t.__k = n.__k, t.__k.some(function(S) {
          S && (S.__ = t);
        }), q.push.apply(s.__h, s._sb), s._sb = [], s.__h.length && _.push(s);
        break e;
      }
      s.componentWillUpdate != null && s.componentWillUpdate(p, s.__s, $), m && s.componentDidUpdate != null && s.__h.push(function() {
        s.componentDidUpdate(f, k, T);
      });
    }
    if (s.context = $, s.props = p, s.__P = e, s.__e = !1, N = y.__r, M = 0, m) s.state = s.__s, s.__d = !1, N && N(t), d = s.render(s.props, s.state, s.context), q.push.apply(s.__h, s._sb), s._sb = [];
    else do
      s.__d = !1, N && N(t), d = s.render(s.props, s.state, s.context), s.state = s.__s;
    while (s.__d && ++M < 25);
    s.state = s.__s, s.getChildContext != null && (o = E(E({}, o), s.getChildContext())), m && !h && s.getSnapshotBeforeUpdate != null && (T = s.getSnapshotBeforeUpdate(f, k)), R = d != null && d.type === G && d.key == null ? Ae(d.props.children) : d, c = $e(e, V(R) ? R : [R], t, n, o, l, r, _, c, u, a), s.base = t.__e, t.__u &= -161, s.__h.length && _.push(s), b && (s.__E = s.__ = null);
  } catch (S) {
    if (t.__v = null, u || r != null) if (S.then) {
      for (t.__u |= u ? 160 : 128; c && c.nodeType == 8 && c.nextSibling; ) c = c.nextSibling;
      r[r.indexOf(c)] = null, t.__e = c;
    } else {
      for (F = r.length; F--; ) te(r[F]);
      Y(t);
    }
    else t.__e = n.__e, t.__k = n.__k, S.then || Y(t);
    y.__e(S, t, n);
  }
  else r == null && t.__v == n.__v ? (t.__k = n.__k, t.__e = n.__e) : c = t.__e = Ie(n.__e, t, n, o, l, r, _, u, a);
  return (d = y.diffed) && d(t), 128 & t.__u ? void 0 : c;
}
function Y(e) {
  e && (e.__c && (e.__c.__e = !0), e.__k && e.__k.some(Y));
}
function Ee(e, t, n) {
  for (var o = 0; o < n.length; o++) re(n[o], n[++o], n[++o]);
  y.__c && y.__c(t, e), e.some(function(l) {
    try {
      e = l.__h, l.__h = [], e.some(function(r) {
        r.call(l);
      });
    } catch (r) {
      y.__e(r, l.__v);
    }
  });
}
function Ae(e) {
  return typeof e != "object" || e == null || e.__b > 0 ? e : V(e) ? e.map(Ae) : E({}, e);
}
function Ie(e, t, n, o, l, r, _, c, u) {
  var a, d, s, h, f, k, T, b = n.props || W, p = t.props, m = t.type;
  if (m == "svg" ? l = "http://www.w3.org/2000/svg" : m == "math" ? l = "http://www.w3.org/1998/Math/MathML" : l || (l = "http://www.w3.org/1999/xhtml"), r != null) {
    for (a = 0; a < r.length; a++) if ((f = r[a]) && "setAttribute" in f == !!m && (m ? f.localName == m : f.nodeType == 3)) {
      e = f, r[a] = null;
      break;
    }
  }
  if (e == null) {
    if (m == null) return document.createTextNode(p);
    e = document.createElementNS(l, m, p.is && p), c && (y.__m && y.__m(t, r), c = !1), r = null;
  }
  if (m == null) b === p || c && e.data == p || (e.data = p);
  else {
    if (r = r && z.call(e.childNodes), !c && r != null) for (b = {}, a = 0; a < e.attributes.length; a++) b[(f = e.attributes[a]).name] = f.value;
    for (a in b) f = b[a], a == "dangerouslySetInnerHTML" ? s = f : a == "children" || a in p || a == "value" && "defaultValue" in p || a == "checked" && "defaultChecked" in p || L(e, a, null, f, l);
    for (a in p) f = p[a], a == "children" ? h = f : a == "dangerouslySetInnerHTML" ? d = f : a == "value" ? k = f : a == "checked" ? T = f : c && typeof f != "function" || b[a] === f || L(e, a, f, b[a], l);
    if (d) c || s && (d.__html == s.__html || d.__html == e.innerHTML) || (e.innerHTML = d.__html), t.__k = [];
    else if (s && (e.innerHTML = ""), $e(t.type == "template" ? e.content : e, V(h) ? h : [h], t, n, o, m == "foreignObject" ? "http://www.w3.org/1999/xhtml" : l, r, _, r ? r[0] : n.__k && U(n, 0), c, u), r != null) for (a = r.length; a--; ) te(r[a]);
    c || (a = "value", m == "progress" && k == null ? e.removeAttribute("value") : k != null && (k !== e[a] || m == "progress" && !k || m == "option" && k != b[a]) && L(e, a, k, b[a], l), a = "checked", T != null && T != e[a] && L(e, a, T, b[a], l));
  }
  return e;
}
function re(e, t, n) {
  try {
    if (typeof e == "function") {
      var o = typeof e.__u == "function";
      o && e.__u(), o && t == null || (e.__u = e(t));
    } else e.current = t;
  } catch (l) {
    y.__e(l, n);
  }
}
function De(e, t, n) {
  var o, l;
  if (y.unmount && y.unmount(e), (o = e.ref) && (o.current && o.current != e.__e || re(o, null, t)), (o = e.__c) != null) {
    if (o.componentWillUnmount) try {
      o.componentWillUnmount();
    } catch (r) {
      y.__e(r, t);
    }
    o.base = o.__P = null;
  }
  if (o = e.__k) for (l = 0; l < o.length; l++) o[l] && De(o[l], t, n || typeof e.type != "function");
  n || te(e.__e), e.__c = e.__ = e.__e = void 0;
}
function je(e, t, n) {
  return this.constructor(e, n);
}
function Oe(e, t, n) {
  var o, l, r, _;
  t == document && (t = document.documentElement), y.__ && y.__(e, t), l = (o = !1) ? null : t.__k, r = [], _ = [], ne(t, e = t.__k = He(G, null, [e]), l || W, W, t.namespaceURI, l ? null : t.firstChild ? z.call(t.childNodes) : null, r, l ? l.__e : t.firstChild, o, _), Ee(r, e, _);
}
z = q.slice, y = { __e: function(e, t, n, o) {
  for (var l, r, _; t = t.__; ) if ((l = t.__c) && !l.__) try {
    if ((r = l.constructor) && r.getDerivedStateFromError != null && (l.setState(r.getDerivedStateFromError(e)), _ = l.__d), l.componentDidCatch != null && (l.componentDidCatch(e, o || {}), _ = l.__d), _) return l.__E = l;
  } catch (c) {
    e = c;
  }
  throw e;
} }, ke = 0, j.prototype.setState = function(e, t) {
  var n;
  n = this.__s != null && this.__s != this.state ? this.__s : this.__s = E({}, this.state), typeof e == "function" && (e = e(E({}, n), this.props)), e && E(n, e), e != null && this.__v && (t && this._sb.push(t), _e(this));
}, j.prototype.forceUpdate = function(e) {
  this.__v && (this.__e = !0, e && this.__h.push(e), _e(this));
}, j.prototype.render = G, D = [], we = typeof Promise == "function" ? Promise.prototype.then.bind(Promise.resolve()) : setTimeout, Se = function(e, t) {
  return e.__v.__b - t.__v.__b;
}, B.__r = 0, Te = /(PointerCapture)$|Capture$/i, ee = 0, X = ce(!1), Q = ce(!0);
var We = 0;
function i(e, t, n, o, l, r) {
  t || (t = {});
  var _, c, u = t;
  if ("ref" in u) for (c in u = {}, t) c == "ref" ? _ = t[c] : u[c] = t[c];
  var a = { type: e, props: u, key: n, ref: _, __k: null, __: null, __b: 0, __e: null, __c: null, constructor: void 0, __v: --We, __i: -1, __u: 0, __source: l, __self: r };
  if (typeof e == "function" && (_ = e.defaultProps)) for (c in _) u[c] === void 0 && (u[c] = _[c]);
  return y.vnode && y.vnode(a), a;
}
var H, g, J, ue, P = 0, Ne = [], w = y, de = w.__b, fe = w.__r, he = w.diffed, pe = w.__c, me = w.unmount, ye = w.__;
function oe(e, t) {
  w.__h && w.__h(g, e, P || t), P = 0;
  var n = g.__H || (g.__H = { __: [], __h: [] });
  return e >= n.__.length && n.__.push({}), n.__[e];
}
function x(e) {
  return P = 1, qe(Ue, e);
}
function qe(e, t, n) {
  var o = oe(H++, 2);
  if (o.t = e, !o.__c && (o.__ = [Ue(void 0, t), function(c) {
    var u = o.__N ? o.__N[0] : o.__[0], a = o.t(u, c);
    u !== a && (o.__N = [a, o.__[1]], o.__c.setState({}));
  }], o.__c = g, !g.__f)) {
    var l = function(c, u, a) {
      if (!o.__c.__H) return !0;
      var d = o.__c.__H.__.filter(function(h) {
        return h.__c;
      });
      if (d.every(function(h) {
        return !h.__N;
      })) return !r || r.call(this, c, u, a);
      var s = o.__c.props !== c;
      return d.some(function(h) {
        if (h.__N) {
          var f = h.__[0];
          h.__ = h.__N, h.__N = void 0, f !== h.__[0] && (s = !0);
        }
      }), r && r.call(this, c, u, a) || s;
    };
    g.__f = !0;
    var r = g.shouldComponentUpdate, _ = g.componentWillUpdate;
    g.componentWillUpdate = function(c, u, a) {
      if (this.__e) {
        var d = r;
        r = void 0, l(c, u, a), r = d;
      }
      _ && _.call(this, c, u, a);
    }, g.shouldComponentUpdate = l;
  }
  return o.__N || o.__;
}
function le(e, t) {
  var n = oe(H++, 3);
  !w.__s && Re(n.__H, t) && (n.__ = e, n.u = t, g.__H.__h.push(n));
}
function se(e) {
  return P = 5, K(function() {
    return { current: e };
  }, []);
}
function K(e, t) {
  var n = oe(H++, 7);
  return Re(n.__H, t) && (n.__ = e(), n.__H = t, n.__h = e), n.__;
}
function A(e, t) {
  return P = 8, K(function() {
    return e;
  }, t);
}
function Be() {
  for (var e; e = Ne.shift(); ) {
    var t = e.__H;
    if (e.__P && t) try {
      t.__h.some(O), t.__h.some(Z), t.__h = [];
    } catch (n) {
      t.__h = [], w.__e(n, e.__v);
    }
  }
}
w.__b = function(e) {
  g = null, de && de(e);
}, w.__ = function(e, t) {
  e && t.__k && t.__k.__m && (e.__m = t.__k.__m), ye && ye(e, t);
}, w.__r = function(e) {
  fe && fe(e), H = 0;
  var t = (g = e.__c).__H;
  t && (J === g ? (t.__h = [], g.__h = [], t.__.some(function(n) {
    n.__N && (n.__ = n.__N), n.u = n.__N = void 0;
  })) : (t.__h.some(O), t.__h.some(Z), t.__h = [], H = 0)), J = g;
}, w.diffed = function(e) {
  he && he(e);
  var t = e.__c;
  t && t.__H && (t.__H.__h.length && (Ne.push(t) !== 1 && ue === w.requestAnimationFrame || ((ue = w.requestAnimationFrame) || Ke)(Be)), t.__H.__.some(function(n) {
    n.u && (n.__H = n.u), n.u = void 0;
  })), J = g = null;
}, w.__c = function(e, t) {
  t.some(function(n) {
    try {
      n.__h.some(O), n.__h = n.__h.filter(function(o) {
        return !o.__ || Z(o);
      });
    } catch (o) {
      t.some(function(l) {
        l.__h && (l.__h = []);
      }), t = [], w.__e(o, n.__v);
    }
  }), pe && pe(e, t);
}, w.unmount = function(e) {
  me && me(e);
  var t, n = e.__c;
  n && n.__H && (n.__H.__.some(function(o) {
    try {
      O(o);
    } catch (l) {
      t = l;
    }
  }), n.__H = void 0, t && w.__e(t, n.__v));
};
var ve = typeof requestAnimationFrame == "function";
function Ke(e) {
  var t, n = function() {
    clearTimeout(o), ve && cancelAnimationFrame(t), setTimeout(e);
  }, o = setTimeout(n, 35);
  ve && (t = requestAnimationFrame(n));
}
function O(e) {
  var t = g, n = e.__c;
  typeof n == "function" && (e.__c = void 0, n()), g = t;
}
function Z(e) {
  var t = g;
  e.__c = e.__(), g = t;
}
function Re(e, t) {
  return !e || e.length !== t.length || t.some(function(n, o) {
    return n !== e[o];
  });
}
function Ue(e, t) {
  return typeof t == "function" ? t(e) : t;
}
async function ze(e) {
  const t = e ? `/api/snapshot?dashboard=${encodeURIComponent(e)}` : "/api/snapshot", n = await fetch(t);
  if (!n.ok) throw new Error(`Snapshot fetch failed: ${n.status}`);
  return n.json();
}
async function Ve(e) {
  const t = await fetch(`/api/notifications/${encodeURIComponent(e)}/dismiss`, { method: "POST" });
  if (!t.ok) throw new Error(`Dismiss failed: ${t.status}`);
}
const Ge = 15e3;
function Je(e) {
  const [t, n] = x(null), [o, l] = x(!0), [r, _] = x(!1), [c, u] = x(null), a = se(!1), d = A(
    async (h = !1) => {
      if (!a.current) {
        a.current = !0, h && _(!0);
        try {
          const f = await ze(e);
          n(f), u(null);
        } catch (f) {
          u(f instanceof Error ? f.message : "Unknown error");
        } finally {
          a.current = !1, h ? _(!1) : l(!1);
        }
      }
    },
    [e]
  );
  le(() => {
    l(!0), d(!1);
    const h = setInterval(() => d(!0), Ge);
    return () => clearInterval(h);
  }, [d]);
  const s = A(() => d(!0), [d]);
  return { snapshot: t, loading: o, refreshing: r, error: c, refresh: s };
}
const be = { unread: "all", reason: "", repository: "" };
function Xe() {
  const [e, t] = x(be), n = A(
    (l, r) => {
      t((_) => ({ ..._, [l]: r }));
    },
    []
  ), o = A(() => t(be), []);
  return { filters: e, setFilter: n, clearFilters: o };
}
function Qe(e = "score", t = "desc") {
  const [n, o] = x(e), [l, r] = x(t), _ = A(
    (c) => {
      c === n ? r((u) => u === "asc" ? "desc" : "asc") : (o(c), r("desc"));
    },
    [n]
  );
  return { sortColumn: n, sortDirection: l, handleSort: _ };
}
function Ye(e, t) {
  const [n, o] = x(/* @__PURE__ */ new Map()), l = se(n);
  le(() => {
    l.current = n;
  }, [n]);
  const r = A((u) => {
    const a = l.current.get(u);
    a && clearTimeout(a.timerId);
    const d = setTimeout(async () => {
      try {
        await Ve(u), e();
      } catch (s) {
        t(s instanceof Error ? s.message : "Dismiss failed");
      } finally {
        o((s) => {
          const h = new Map(s);
          return h.delete(u), h;
        });
      }
    }, 3e3);
    o((s) => {
      const h = new Map(s);
      return h.set(u, { threadId: u, timerId: d }), h;
    });
  }, [e, t]), _ = A((u) => {
    const a = l.current.get(u);
    a && (clearTimeout(a.timerId), o((d) => {
      const s = new Map(d);
      return s.delete(u), s;
    }));
  }, []), c = A(() => {
    l.current.forEach((u) => clearTimeout(u.timerId)), o(/* @__PURE__ */ new Map());
  }, []);
  return { pending: n, dismiss: r, undo: _, undoAll: c };
}
function Ze({ onRefresh: e, onFocusFilters: t, onDismissFocused: n }) {
  le(() => {
    function o(l) {
      var c, u, a;
      const r = l.target, _ = ["INPUT", "SELECT", "TEXTAREA"].includes(r.tagName);
      if (l.key === "Escape") {
        (c = document.activeElement) == null || c.blur();
        return;
      }
      if (l.key === "/") {
        l.preventDefault(), t();
        return;
      }
      if (!_) {
        if (l.key === "r" || l.key === "R") {
          e();
          return;
        }
        if (l.key === "d" || l.key === "D") {
          const d = document.activeElement;
          (d == null ? void 0 : d.tagName) === "TR" && n();
          return;
        }
        if (l.key === "j" || l.key === "J") {
          const d = Array.from(document.querySelectorAll("tr[tabindex='0']")), s = d.indexOf(document.activeElement);
          (u = d[s + 1]) == null || u.focus();
          return;
        }
        if (l.key === "k" || l.key === "K") {
          const d = Array.from(document.querySelectorAll("tr[tabindex='0']")), s = d.indexOf(document.activeElement);
          (a = d[s - 1]) == null || a.focus();
          return;
        }
        if (l.key === "Enter") {
          const d = document.activeElement;
          if ((d == null ? void 0 : d.tagName) === "TR") {
            const s = d.querySelector("a[href]");
            s && window.open(s.href, "_blank");
          }
        }
      }
    }
    return document.addEventListener("keydown", o), () => document.removeEventListener("keydown", o);
  }, [e, t, n]);
}
function et({
  dashboardNames: e,
  currentDashboard: t,
  onDashboardChange: n,
  onRefresh: o,
  refreshing: l,
  summary: r
}) {
  return /* @__PURE__ */ i("div", { class: "toolbar-row", children: [
    /* @__PURE__ */ i("span", { class: "app-name", children: "Corvix" }),
    r && /* @__PURE__ */ i("span", { class: "inline-stats", children: [
      r.unread_items + r.read_items,
      " notifications · ",
      r.unread_items,
      " unread · ",
      r.repository_count,
      " repos"
    ] }),
    /* @__PURE__ */ i("div", { class: "toolbar-right", children: [
      e.length > 1 && /* @__PURE__ */ i(
        "select",
        {
          value: t ?? "",
          onChange: (_) => n(_.target.value),
          "aria-label": "Select dashboard",
          children: e.map((_) => /* @__PURE__ */ i("option", { value: _, children: _ }, _))
        }
      ),
      /* @__PURE__ */ i(
        "button",
        {
          type: "button",
          class: `refresh-btn${l ? " refreshing" : ""}`,
          onClick: o,
          "aria-label": "Refresh",
          disabled: l,
          children: l ? "↻ Refreshing" : "↻ Refresh"
        }
      )
    ] })
  ] });
}
function tt({ filters: e, items: t, onFilterChange: n, onClearFilters: o, generatedAt: l, filterBarRef: r }) {
  const _ = Array.from(new Set(t.map((u) => u.reason))).sort(), c = Array.from(new Set(t.map((u) => u.repository))).sort();
  return /* @__PURE__ */ i("div", { class: "filter-row", children: [
    /* @__PURE__ */ i(
      "select",
      {
        ref: r,
        value: e.unread,
        onChange: (u) => n("unread", u.target.value),
        "aria-label": "Unread state filter",
        children: [
          /* @__PURE__ */ i("option", { value: "all", children: "All" }),
          /* @__PURE__ */ i("option", { value: "unread", children: "Unread only" }),
          /* @__PURE__ */ i("option", { value: "read", children: "Read only" })
        ]
      }
    ),
    /* @__PURE__ */ i(
      "select",
      {
        value: e.reason,
        onChange: (u) => n("reason", u.target.value),
        "aria-label": "Reason filter",
        children: [
          /* @__PURE__ */ i("option", { value: "", children: "All reasons" }),
          _.map((u) => /* @__PURE__ */ i("option", { value: u, children: u }, u))
        ]
      }
    ),
    /* @__PURE__ */ i(
      "select",
      {
        value: e.repository,
        onChange: (u) => n("repository", u.target.value),
        "aria-label": "Repository filter",
        children: [
          /* @__PURE__ */ i("option", { value: "", children: "All repositories" }),
          c.map((u) => /* @__PURE__ */ i("option", { value: u, children: u }, u))
        ]
      }
    ),
    /* @__PURE__ */ i("button", { type: "button", onClick: o, children: "Clear" }),
    l && /* @__PURE__ */ i("span", { class: "snapshot-time", children: [
      "Snapshot: ",
      new Date(l).toLocaleTimeString()
    ] })
  ] });
}
const nt = [
  { key: "subject_title", label: "Title" },
  { key: "repository", label: "Repository" },
  { key: "subject_type", label: "Type", className: "hide-mobile" },
  { key: "reason", label: "Reason", className: "hide-mobile" },
  { key: "score", label: "Score" },
  { key: "updated_at", label: "Updated" }
];
function rt({ sortColumn: e, sortDirection: t, onSort: n }) {
  return /* @__PURE__ */ i("thead", { children: /* @__PURE__ */ i("tr", { children: [
    /* @__PURE__ */ i("th", { class: "col-status", "aria-label": "Unread status" }),
    nt.map(({ key: o, label: l, className: r }) => /* @__PURE__ */ i(
      "th",
      {
        class: [r, "sortable", e === o ? "sort-active" : ""].filter(Boolean).join(" "),
        onClick: () => n(o),
        "aria-sort": e === o ? t === "asc" ? "ascending" : "descending" : "none",
        children: [
          l,
          e === o && /* @__PURE__ */ i("span", { class: "sort-arrow", "aria-hidden": "true", children: t === "asc" ? " ▲" : " ▼" })
        ]
      },
      o
    )),
    /* @__PURE__ */ i("th", { class: "col-actions", "aria-label": "Actions" })
  ] }) });
}
function ot(e) {
  const t = Date.now() - new Date(e).getTime(), n = Math.floor(t / 6e4);
  if (n < 60) return `${n}m ago`;
  const o = Math.floor(n / 60);
  return o < 24 ? `${o}h ago` : `${Math.floor(o / 24)}d ago`;
}
function lt({ item: e, onDismiss: t, isPendingDismissal: n }) {
  function o(l) {
    l.key === "Enter" && e.web_url && window.open(e.web_url, "_blank"), (l.key === "d" || l.key === "D") && !l.target.matches("button") && t(e.thread_id);
  }
  return /* @__PURE__ */ i(
    "tr",
    {
      class: [
        "notification-row",
        e.unread ? "unread" : "read",
        n ? "dismissing" : ""
      ].filter(Boolean).join(" "),
      tabIndex: 0,
      onKeyDown: o,
      "aria-label": e.subject_title,
      children: [
        /* @__PURE__ */ i("td", { class: "col-status", "aria-hidden": "true", children: /* @__PURE__ */ i("span", { class: `unread-dot ${e.unread ? "dot-unread" : "dot-read"}` }) }),
        /* @__PURE__ */ i("td", { class: "col-title", "data-label": "Title", children: e.web_url ? /* @__PURE__ */ i("a", { href: e.web_url, target: "_blank", rel: "noopener noreferrer", class: "title-link", children: e.subject_title }) : /* @__PURE__ */ i("span", { class: "title-link", children: e.subject_title }) }),
        /* @__PURE__ */ i("td", { class: "col-repository", "data-label": "Repository", children: /* @__PURE__ */ i("span", { class: "repo-label", children: e.repository }) }),
        /* @__PURE__ */ i("td", { class: "col-type hide-mobile", "data-label": "Type", children: e.subject_type }),
        /* @__PURE__ */ i("td", { class: "col-reason hide-mobile", "data-label": "Reason", children: e.reason }),
        /* @__PURE__ */ i("td", { class: "col-score", "data-label": "Score", children: /* @__PURE__ */ i("span", { class: "score-value", children: e.score.toFixed(1) }) }),
        /* @__PURE__ */ i("td", { class: "col-updated", "data-label": "Updated", children: /* @__PURE__ */ i("span", { title: e.updated_at, children: ot(e.updated_at) }) }),
        /* @__PURE__ */ i("td", { class: "col-actions", children: /* @__PURE__ */ i(
          "button",
          {
            type: "button",
            class: "dismiss-btn",
            "aria-label": `Dismiss ${e.subject_title}`,
            onClick: () => t(e.thread_id),
            children: "✕"
          }
        ) })
      ]
    }
  );
}
function st(e, t, n) {
  const o = [...e].sort((l, r) => {
    let _ = l[t], c = r[t];
    return typeof _ == "string" && typeof c == "string" && (_ = _.toLowerCase(), c = c.toLowerCase()), _ < c ? -1 : _ > c ? 1 : 0;
  });
  return n === "desc" ? o.reverse() : o;
}
function it({
  groups: e,
  sortColumn: t,
  sortDirection: n,
  onSort: o,
  onDismiss: l,
  pendingDismissals: r
}) {
  return /* @__PURE__ */ i("table", { class: "notification-table", children: [
    /* @__PURE__ */ i(rt, { sortColumn: t, sortDirection: n, onSort: o }),
    /* @__PURE__ */ i("tbody", { children: e.map((c) => {
      const u = st(c.items, t, n);
      return [
        /* @__PURE__ */ i("tr", { class: "group-header-row", children: /* @__PURE__ */ i("td", { colSpan: 8, class: "group-header-cell", children: [
          c.name,
          " ",
          /* @__PURE__ */ i("span", { class: "group-count", children: [
            "(",
            c.items.length,
            ")"
          ] })
        ] }) }, `group-${c.name}`),
        ...u.map((a) => /* @__PURE__ */ i(
          lt,
          {
            item: a,
            onDismiss: l,
            isPendingDismissal: r.has(a.thread_id)
          },
          a.thread_id
        ))
      ];
    }) })
  ] });
}
function _t({ count: e, onUndoAll: t }) {
  return e === 0 ? null : /* @__PURE__ */ i("div", { class: "undo-toast", role: "status", "aria-live": "polite", children: [
    /* @__PURE__ */ i("span", { children: [
      e,
      " notification",
      e > 1 ? "s" : "",
      " dismissing…"
    ] }),
    /* @__PURE__ */ i("button", { type: "button", onClick: t, children: "Undo" })
  ] });
}
function ge({ hasFilters: e, totalItems: t, onClearFilters: n, onRetry: o, error: l }) {
  return l ? /* @__PURE__ */ i("div", { class: "empty-state error-state", children: [
    /* @__PURE__ */ i("p", { class: "empty-title", children: "Failed to load" }),
    /* @__PURE__ */ i("p", { class: "empty-body", children: l }),
    /* @__PURE__ */ i("button", { type: "button", onClick: o, children: "Retry" })
  ] }) : t === 0 ? /* @__PURE__ */ i("div", { class: "empty-state", children: [
    /* @__PURE__ */ i("p", { class: "empty-title", children: "All clear" }),
    /* @__PURE__ */ i("p", { class: "empty-body", children: "No notifications in this dashboard." })
  ] }) : /* @__PURE__ */ i("div", { class: "empty-state", children: [
    /* @__PURE__ */ i("p", { class: "empty-title", children: "No results" }),
    /* @__PURE__ */ i("p", { class: "empty-body", children: "No notifications match the current filters." }),
    e && /* @__PURE__ */ i("button", { type: "button", onClick: n, children: "Clear filters" })
  ] });
}
function at() {
  return /* @__PURE__ */ i("table", { class: "notification-table", "aria-label": "Loading notifications", children: [
    /* @__PURE__ */ i("thead", { children: /* @__PURE__ */ i("tr", { children: [
      /* @__PURE__ */ i("th", { style: { width: "28px" } }),
      /* @__PURE__ */ i("th", { children: "Title" }),
      /* @__PURE__ */ i("th", { children: "Repository" }),
      /* @__PURE__ */ i("th", { class: "hide-mobile", children: "Type" }),
      /* @__PURE__ */ i("th", { class: "hide-mobile", children: "Reason" }),
      /* @__PURE__ */ i("th", { children: "Score" }),
      /* @__PURE__ */ i("th", { children: "Updated" }),
      /* @__PURE__ */ i("th", { style: { width: "36px" } })
    ] }) }),
    /* @__PURE__ */ i("tbody", { children: Array.from({ length: 9 }, (e, t) => /* @__PURE__ */ i("tr", { class: "skeleton-row", children: [
      /* @__PURE__ */ i("td", { children: /* @__PURE__ */ i("span", { class: "skeleton dot-skeleton" }) }),
      /* @__PURE__ */ i("td", { children: /* @__PURE__ */ i("span", { class: "skeleton title-skeleton" }) }),
      /* @__PURE__ */ i("td", { children: /* @__PURE__ */ i("span", { class: "skeleton repo-skeleton" }) }),
      /* @__PURE__ */ i("td", { class: "hide-mobile", children: /* @__PURE__ */ i("span", { class: "skeleton short-skeleton" }) }),
      /* @__PURE__ */ i("td", { class: "hide-mobile", children: /* @__PURE__ */ i("span", { class: "skeleton short-skeleton" }) }),
      /* @__PURE__ */ i("td", { children: /* @__PURE__ */ i("span", { class: "skeleton score-skeleton" }) }),
      /* @__PURE__ */ i("td", { children: /* @__PURE__ */ i("span", { class: "skeleton time-skeleton" }) }),
      /* @__PURE__ */ i("td", {})
    ] }, t)) })
  ] });
}
function ct() {
  const [e, t] = x(void 0), [n, o] = x(null), l = se(null), { snapshot: r, loading: _, refreshing: c, error: u, refresh: a } = Je(e), { filters: d, setFilter: s, clearFilters: h } = Xe(), { sortColumn: f, sortDirection: k, handleSort: T } = Qe("score", "desc"), { pending: b, dismiss: p, undoAll: m } = Ye(a, o), C = K(() => r ? r.groups.flatMap((v) => v.items) : [], [r]), $ = K(() => r ? r.groups.map((v) => ({
    ...v,
    items: v.items.filter((S) => !(b.has(S.thread_id) || d.unread !== "all" && (d.unread === "unread" && !S.unread || d.unread === "read" && S.unread) || d.reason && S.reason !== d.reason || d.repository && S.repository !== d.repository))
  })).filter((v) => v.items.length > 0) : [], [r, d, b]), N = d.unread !== "all" || d.reason !== "" || d.repository !== "", M = A(() => {
    const v = document.activeElement;
    if ((v == null ? void 0 : v.tagName) === "TR") {
      const S = v.getAttribute("data-thread-id");
      S && p(S);
    }
  }, [p]);
  Ze({
    onRefresh: a,
    onFocusFilters: () => {
      var v;
      return (v = l.current) == null ? void 0 : v.focus();
    },
    onDismissFocused: M
  });
  const R = (r == null ? void 0 : r.dashboard_names) ?? [], F = e ?? R[0] ?? null;
  return /* @__PURE__ */ i("div", { class: "shell", children: [
    c && /* @__PURE__ */ i("div", { class: "refresh-bar", "aria-hidden": "true" }),
    /* @__PURE__ */ i(
      et,
      {
        dashboardNames: R,
        currentDashboard: F,
        onDashboardChange: t,
        onRefresh: a,
        refreshing: c,
        summary: (r == null ? void 0 : r.summary) ?? null
      }
    ),
    r && /* @__PURE__ */ i(
      tt,
      {
        filters: d,
        items: C,
        onFilterChange: s,
        onClearFilters: h,
        generatedAt: r.generated_at,
        filterBarRef: l
      }
    ),
    /* @__PURE__ */ i("main", { class: "board", children: _ ? /* @__PURE__ */ i(at, {}) : u ? /* @__PURE__ */ i(
      ge,
      {
        hasFilters: !1,
        totalItems: 0,
        onClearFilters: h,
        onRetry: a,
        error: u
      }
    ) : $.length === 0 ? /* @__PURE__ */ i(
      ge,
      {
        hasFilters: N,
        totalItems: (r == null ? void 0 : r.total_items) ?? 0,
        onClearFilters: h,
        onRetry: a
      }
    ) : /* @__PURE__ */ i(
      it,
      {
        groups: $,
        sortColumn: f,
        sortDirection: k,
        onSort: T,
        onDismiss: p,
        pendingDismissals: new Set(b.keys())
      }
    ) }),
    n && /* @__PURE__ */ i("div", { class: "error-toast", role: "alert", children: [
      n,
      /* @__PURE__ */ i("button", { type: "button", onClick: () => o(null), children: "✕" })
    ] }),
    /* @__PURE__ */ i(_t, { count: b.size, onUndoAll: m })
  ] });
}
Oe(/* @__PURE__ */ i(ct, {}), document.getElementById("app"));
