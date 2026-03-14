/* ============================================================
   姚彦博个人网站 — JavaScript
   ============================================================ */

(function () {
  "use strict";

  /* ---------- 元素引用 ---------- */
  const navbar      = document.getElementById("navbar");
  const navMenu     = document.getElementById("navMenu");
  const hamburger   = document.getElementById("hamburger");
  const themeToggle = document.getElementById("themeToggle");
  const themeIcon   = themeToggle.querySelector(".theme-icon");
  const scrollTopBtn = document.getElementById("scrollTop");
  const contactForm = document.getElementById("contactForm");
  const formFeedback = document.getElementById("formFeedback");
  const yearSpan    = document.getElementById("year");

  /* ---------- 当前年份 ---------- */
  if (yearSpan) yearSpan.textContent = new Date().getFullYear();

  /* ============================================================
     主题切换（深色 / 浅色）
     ============================================================ */
  const THEME_KEY = "yyb-theme";

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    themeIcon.textContent = theme === "dark" ? "☀️" : "🌙";
    localStorage.setItem(THEME_KEY, theme);
  }

  // 初始化主题
  const savedTheme = localStorage.getItem(THEME_KEY) ||
    (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  applyTheme(savedTheme);

  themeToggle.addEventListener("click", function () {
    const current = document.documentElement.getAttribute("data-theme");
    applyTheme(current === "dark" ? "light" : "dark");
  });

  /* ============================================================
     导航栏滚动效果
     ============================================================ */
  function onScroll() {
    if (window.scrollY > 60) {
      navbar.classList.add("scrolled");
    } else {
      navbar.classList.remove("scrolled");
    }

    // 回到顶部按钮
    if (window.scrollY > 400) {
      scrollTopBtn.classList.add("visible");
    } else {
      scrollTopBtn.classList.remove("visible");
    }

    // 高亮当前导航项
    highlightNav();
  }

  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  /* ---------- 高亮当前 Section 对应的导航链接 ---------- */
  const sections = Array.from(document.querySelectorAll("section[id]"));
  const navLinks = Array.from(document.querySelectorAll(".nav-link"));

  function highlightNav() {
    const scrollPos = window.scrollY + 100;
    let current = "";
    sections.forEach(function (sec) {
      if (sec.offsetTop <= scrollPos) {
        current = sec.id;
      }
    });
    navLinks.forEach(function (link) {
      link.classList.toggle(
        "active",
        link.getAttribute("href") === "#" + current
      );
    });
  }

  /* ============================================================
     汉堡菜单（移动端）
     ============================================================ */
  hamburger.addEventListener("click", function () {
    const isOpen = navMenu.classList.toggle("open");
    hamburger.setAttribute("aria-expanded", isOpen);
  });

  // 点击导航链接后关闭菜单
  navLinks.forEach(function (link) {
    link.addEventListener("click", function () {
      navMenu.classList.remove("open");
      hamburger.setAttribute("aria-expanded", "false");
    });
  });

  // 点击外部关闭菜单
  document.addEventListener("click", function (e) {
    if (!navbar.contains(e.target)) {
      navMenu.classList.remove("open");
      hamburger.setAttribute("aria-expanded", "false");
    }
  });

  /* ============================================================
     回到顶部
     ============================================================ */
  scrollTopBtn.addEventListener("click", function () {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  /* ============================================================
     技能进度条动画（Intersection Observer）
     ============================================================ */
  const skillFills = Array.from(document.querySelectorAll(".skill-fill"));

  if ("IntersectionObserver" in window) {
    const skillObserver = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.style.width = entry.target.dataset.width;
            skillObserver.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.3 }
    );

    skillFills.forEach(function (fill) {
      // 保存目标宽度，初始置 0
      fill.dataset.width = fill.style.width;
      fill.style.width = "0";
      skillObserver.observe(fill);
    });
  } else {
    // 不支持 Observer 时直接显示
    skillFills.forEach(function (fill) {
      fill.style.transition = "none";
    });
  }

  /* ============================================================
     卡片入场动画（Intersection Observer）
     ============================================================ */
  const animatedEls = Array.from(
    document.querySelectorAll(".card, .blog-card, .stat-card, .social-link")
  );

  // 初始隐藏
  animatedEls.forEach(function (el, i) {
    el.style.opacity = "0";
    el.style.transform = "translateY(24px)";
    el.style.transition =
      "opacity .5s ease " + i * 0.07 + "s, transform .5s ease " + i * 0.07 + "s";
  });

  if ("IntersectionObserver" in window) {
    const cardObserver = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.style.opacity = "1";
            entry.target.style.transform = "translateY(0)";
            cardObserver.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12 }
    );
    animatedEls.forEach(function (el) { cardObserver.observe(el); });
  } else {
    animatedEls.forEach(function (el) {
      el.style.opacity = "1";
      el.style.transform = "none";
    });
  }

  /* ============================================================
     联系表单
     ============================================================ */
  if (contactForm) {
    contactForm.addEventListener("submit", function (e) {
      e.preventDefault();

      // 简单前端验证
      let valid = true;
      ["name", "email", "message"].forEach(function (fieldName) {
        const el = contactForm.elements[fieldName];
        if (!el.value.trim()) {
          el.classList.add("error");
          valid = false;
        } else {
          el.classList.remove("error");
        }
      });

      const emailEl = contactForm.elements["email"];
      if (emailEl.value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailEl.value)) {
        emailEl.classList.add("error");
        valid = false;
      }

      if (!valid) {
        showFeedback("请填写所有必填项并确认邮箱格式正确。", "error");
        return;
      }

      // 模拟发送（静态网站无后端）
      const submitBtn = contactForm.querySelector("[type=submit]");
      submitBtn.disabled = true;
      submitBtn.textContent = "发送中…";

      setTimeout(function () {
        showFeedback("✅ 留言已收到，感谢你的联系！", "success");
        contactForm.reset();
        submitBtn.disabled = false;
        submitBtn.textContent = "发送留言";
      }, 1200);
    });

    // 输入时清除错误状态
    contactForm.querySelectorAll("input, textarea").forEach(function (el) {
      el.addEventListener("input", function () {
        el.classList.remove("error");
        formFeedback.textContent = "";
        formFeedback.className = "form-feedback";
      });
    });
  }

  function showFeedback(msg, type) {
    formFeedback.textContent = msg;
    formFeedback.className = "form-feedback " + type;
  }

})();
