// ==UserScript==
// @name         网页内容提取脚本
// @namespace    http://tampermonkey.net/
// @version      0.1
// @description  遍历网址列表，提取内容，并保存到本地存储
// @author       你的名字
// @match        https://weibo.com/ttarticle/p/show?id=*
// @grant        none
// ==/UserScript==

(function () {
  "use strict";

  // 检查是否是从脚本中跳转过来的
  const isFromScript = sessionStorage.getItem("isFromScript");

  const urls = getUrls().map((x) => x.url);

  // 初始化状态
  let status = {
    currentUrlIndex: 0,
    // urls: getUrls(), // 这里将会是你的网址列表
    data: [], // 保存提取的内容
  };

  // 检查本地存储以恢复状态
  if (isFromScript) {
    const savedStatus = JSON.parse(sessionStorage.getItem("scriptStatus"));
    if (savedStatus) {
      status = savedStatus;
    }
  }

  // 模拟的内容提取函数
  async function extractContent() {
    await waitForCondition(
      () =>
        isElementPresentAndNotEmpty(
          "#plc_main > div > div > div > div.main_editor > div.title"
        ) &&
        isElementPresentAndNotEmpty(
          "#plc_main > div > div > div > div.main_editor > div.WB_editor_iframe_new"
        ),
      3
    );
    console.log(`当前 ${status.currentUrlIndex}，全部 ${urls.length}`);
    console.log(
      document.querySelector(
        "#plc_main > div > div > div > div.main_editor > div.title"
      ).textContent.trim()
    );
    return {
      title: document.querySelector(
        "#plc_main > div > div > div > div.main_editor > div.title"
      ).textContent.trim(),
      content: document.querySelector(
        "#plc_main > div > div > div > div.main_editor > div.WB_editor_iframe_new"
      ).innerHTML.replace(
        '<fieldset class="line"><legend>以下内容V+或SVIP订阅用户可见</legend></fieldset>',
        ""
      ),
    };
  }

  async function processData(dataList) {
    // 创建一个新的HTML文档结构
    let htmlContent = `<!DOCTYPE html>
  <html lang="zh-cn">
  <head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>文章集合</title>
  </head>
  <body>`;

    // 遍历所有文章数据，将每篇文章的标题和内容添加到HTML文档中
    dataList.forEach((article) => {
      htmlContent += `<h1>${article.title}</h1>${article.content}`;
    });

    // 关闭HTML文档
    htmlContent += `</body></html>`;

    // 使用Blob创建一个可下载的链接
    const blob = new Blob([htmlContent], { type: "text/html" });
    const downloadUrl = URL.createObjectURL(blob);

    // 创建一个临时的a标签来触发下载
    const downloadLink = document.createElement("a");
    downloadLink.href = downloadUrl;
    downloadLink.download = "时代作文.html"; // 设定下载文件名
    document.body.appendChild(downloadLink); // 将a标签添加到文档中
    downloadLink.click(); // 触发下载
    document.body.removeChild(downloadLink); // 移除a标签
    URL.revokeObjectURL(downloadUrl); // 释放创建的URL对象
  }

  // 跳转到下一个URL
  function goToNextUrl() {
    const nextUrl = urls[status.currentUrlIndex];
    if (nextUrl) {
      sessionStorage.setItem("isFromScript", "true");
      sessionStorage.setItem("scriptStatus", JSON.stringify(status));
      window.location.href = nextUrl;
    } else {
      // 所有URL遍历完成
      sessionStorage.removeItem("isFromScript");
      sessionStorage.removeItem("scriptStatus");
      processData(status.data);
    }
  }

  // 等待页面加载完成后提取内容并跳转
  async function onPageLoaded() {
    if (!isFromScript) return; // 如果不是脚本跳转的页面，则不执行操作

    const content = await extractContent();
    status.data.push(content);
    status.currentUrlIndex += 1;

    // 这里可以设置暂停时间
    setTimeout(goToNextUrl, 4000);
  }

  // 添加开始和停止按钮的用户界面
  function addUI() {
    const startButton = document.createElement("button");
    startButton.innerText = "开始";
    startButton.onclick = function () {
      sessionStorage.setItem("isFromScript", "true");
      goToNextUrl();
    };

    const stopButton = document.createElement("button");
    stopButton.innerText = "停止";
    stopButton.onclick = function () {
      sessionStorage.removeItem("isFromScript");
      sessionStorage.removeItem("scriptStatus");
    };

    const uiContainer = document.createElement("div");
    uiContainer.style.position = "fixed";
    uiContainer.style.top = "100px";
    uiContainer.style.right = "10px";
    uiContainer.appendChild(startButton);
    uiContainer.appendChild(stopButton);

    document.body.appendChild(uiContainer);
  }

  // 初始化脚本
  function init() {
    addUI();
    window.addEventListener("load", onPageLoaded);
  }

  init();
})();

function sleep(d) {
  return new Promise((r) => setTimeout(r, d));
}

async function waitForCondition(checkFunction, intervalInSeconds) {
  while (true) {
    // 如果判断函数返回 true，则退出函数
    if (checkFunction()) {
      return;
    }
    // 等待指定的时间间隔后再次进行判断
    await sleep(intervalInSeconds * 1000);
  }
}

function isElementPresentAndNotEmpty(selector) {
  // 使用querySelector尝试获取元素
  const element = document.querySelector(selector);

  // 检查元素是否存在
  if (element) {
    // 获取元素的内容，并使用trim移除可能的前后空白字符
    const content = element.textContent.trim();
    // 判断内容是否不为空
    return content !== "";
  }

  // 如果元素不存在，返回false
  return false;
}

function getUrls() {
  return [
    {
      title: "绍兴的歪脖子树",
      url: "http://t.cn/A6CJFFSS",
    },
    {
      title: "2023年3月6日 晨读",
      url: "http://t.cn/A6CX1o9s",
    },
    {
      title: "特解A：谈师傅的遭遇",
      url: "http://t.cn/A6CaCvlD",
    },
    {
      title: "2023年3月7日 晨读",
      url: "http://t.cn/A6CSPpsH",
    },
    {
      title: "2023年3月8日 晨读",
      url: "http://t.cn/A6CocnuB",
    },
    {
      title: "特解B：我亲爱的香樟树",
      url: "http://t.cn/A6CoJJ43",
    },
    {
      title: "2023年3月9日 晨读",
      url: "http://t.cn/A6CKOi9q",
    },
    {
      title: "特解C：歪脖树的自白",
      url: "http://t.cn/A6CKHEw9",
    },
    {
      title: "2023年3月10日 晨读",
      url: "http://t.cn/A6C9mlXm",
    },
    {
      title: "《静一点》",
      url: "http://t.cn/A6C9gfFd",
    },
    {
      title: "2023年3月13日 晨读",
      url: "http://t.cn/A6C0zkq9",
    },
    {
      title: "通解A：寂静的乡愁",
      url: "http://t.cn/A6C08i1S",
    },
    {
      title: "2023年3月14日 晨读",
      url: "http://t.cn/A6COplG9",
    },
    {
      title: "2023年3月15日 晨读",
      url: "http://t.cn/A6ClTDSN",
    },
    {
      title: "通解B：沉默的匠人",
      url: "http://t.cn/A6CYgXAE",
    },
    {
      title: "2023年3月16日 晨读",
      url: "http://t.cn/A6CQhE3X",
    },
    {
      title: "2023年3月17日 晨读",
      url: "http://t.cn/A6CRck2P",
    },
    {
      title: "特解C：国王的演讲",
      url: "http://t.cn/A6CEzahx",
    },
    {
      title: "2023年3月20日 晨读",
      url: "http://t.cn/A6CmnQic",
    },
    {
      title: "你来了。你来吗？你来啦！",
      url: "http://t.cn/A6CuTGAr",
    },
    {
      title: "2023年3月21日 晨读",
      url: "http://t.cn/A6CuD6o6",
    },
    {
      title: "2023年3月22日 晨读",
      url: "http://t.cn/A6C12Zvx",
    },
    {
      title: "买房",
      url: "http://t.cn/A6C1BNFY",
    },
    {
      title: "通解A：你来了。",
      url: "http://t.cn/A6C1glvP",
    },
    {
      title: "2023年3月23日 晨读",
      url: "http://t.cn/A6Cr6Trp",
    },
    {
      title: "2023年3月24日 晨读",
      url: "http://t.cn/A6Cr6QaY",
    },
    {
      title: "特解B：你来吗？",
      url: "http://t.cn/A6CdEocT",
    },
    {
      title: "2023年3月27日 晨读",
      url: "http://t.cn/A6Ce1Cvs",
    },
    {
      title: "“单调、沉闷的生活就这样发生了改变……”",
      url: "http://t.cn/A6CD90TC",
    },
    {
      title: "2023年3月28日 晨读",
      url: "http://t.cn/A6CkvQIh",
    },
    {
      title: "2023年3月29日 晨读",
      url: "http://t.cn/A6CFy2sa",
    },
    {
      title: "2023年3月30日 晨读",
      url: "http://t.cn/A6CsVeF5",
    },
    {
      title: "特解A：观相",
      url: "http://t.cn/A6CsJgly",
    },
    {
      title: "2023年3月31日 晨读",
      url: "http://t.cn/A6NvXKoM",
    },
    {
      title: "2023年4月1日 晨读",
      url: "http://t.cn/A6NPlAgp",
    },
    {
      title: "特解B：老兵",
      url: "http://t.cn/A6Nhyr2V",
    },
    {
      title: "2023年4月2日 晨读",
      url: "http://t.cn/A6NhT5UP",
    },
    {
      title: "2023年4月4日 晨读",
      url: "http://t.cn/A6NzDhHv",
    },
    {
      title: "2023年4月6日 晨读",
      url: "http://t.cn/A6NA7FAA",
    },
    {
      title: "2023年4月7日 晨读",
      url: "http://t.cn/A6N2tCtB",
    },
    {
      title: "2023年4月10日 晨读",
      url: "http://t.cn/A6NUKE6u",
    },
    {
      title: "改一篇“我的妈妈”",
      url: "http://t.cn/A6NU0eSX",
    },
    {
      title: "2023年4月11日 晨读",
      url: "http://t.cn/A6N40k1w",
    },
    {
      title: "“一定是这样吗？”",
      url: "http://t.cn/A6N4Yr8M",
    },
    {
      title: "2023年4月12日 晨读",
      url: "http://t.cn/A6NbH7h6",
    },
    {
      title: "2023年4月13日 晨读",
      url: "http://t.cn/A6NG3R2B",
    },
    {
      title: "特解A：坏孩子、好孩子",
      url: "http://t.cn/A6NqJZ8p",
    },
    {
      title: "2023年4月14日 晨读",
      url: "http://t.cn/A6NqDFty",
    },
    {
      title: "2023年4月17日 晨读",
      url: "http://t.cn/A6NVt5Yx",
    },
    {
      title: "2023年4月18日 晨读",
      url: "http://t.cn/A6Nf6Nmd",
    },
    {
      title: "引言：初稿、订稿、终稿",
      url: "http://t.cn/A6NIcYbj",
    },
    {
      title: "2023年4月19日 晨读",
      url: "http://t.cn/A6NIOQ8p",
    },
    {
      title: "2023年4月20日 晨读",
      url: "http://t.cn/A6NMuPJe",
    },
    {
      title: "2023年4月21日 晨读",
      url: "http://t.cn/A6NxkRDn",
    },
    {
      title: "改一篇“景物写生”",
      url: "http://t.cn/A6NJhQuu",
    },
    {
      title: "2023年4月24日 晨读",
      url: "http://t.cn/A6NXw70q",
    },
    {
      title: "改一篇“我的家”",
      url: "http://t.cn/A6NX455m",
    },
    {
      title: "2023年4月25日 晨读",
      url: "http://t.cn/A6NatGCW",
    },
    {
      title: "从“树枝笑弯了腰”谈开去：一滴锅边醋",
      url: "http://t.cn/A6NSqOgp",
    },
    {
      title: "2023年4月26日 晨读",
      url: "http://t.cn/A6NSOHiw",
    },
    {
      title: "2023年4月27日 晨读",
      url: "http://t.cn/A6NoFiWL",
    },
    {
      title: "特解B：一根电线杆",
      url: "http://t.cn/A6NK7otQ",
    },
    {
      title: "2023年4月28日 晨读",
      url: "http://t.cn/A6N9bWrG",
    },
    {
      title: "《在劳动中成长》/“话说劳动”",
      url: "http://t.cn/A6NpJChV",
    },
    {
      title: "2023年5月1日 晨读",
      url: "http://t.cn/A6Nps1xs",
    },
    {
      title: "通解A：稚苗",
      url: "http://t.cn/A6N0QZIi",
    },
    {
      title: "2023年5月2日 晨读",
      url: "http://t.cn/A6NOwa0c",
    },
    {
      title: "2023年5月3日 晨读",
      url: "http://t.cn/A6NWcDcu",
    },
    {
      title: "2023年5月4日 晨读",
      url: "http://t.cn/A6NlIMCV",
    },
    {
      title: "2023年5月5日 晨读",
      url: "http://t.cn/A6NjOCFu",
    },
    {
      title: "通解B：稻作",
      url: "http://t.cn/A6NTYTre",
    },
    {
      title: "2023年5月8日 晨读",
      url: "http://t.cn/A6NQqnkR",
    },
    {
      title: "2023年5月9日 晨读",
      url: "http://t.cn/A6N8KnjC",
    },
    {
      title: "2023年5月10日 晨读",
      url: "http://t.cn/A6NRumP9",
    },
    {
      title: "2023年5月11日 晨读",
      url: "http://t.cn/A6NnUtJ8",
    },
    {
      title: "2023年5月12日 晨读",
      url: "http://t.cn/A6NmIAqx",
    },
    {
      title: "引言：积木与宿构的艺术",
      url: "http://t.cn/A6Nu1Wyr",
    },
    {
      title: "2023年5月15日 晨读",
      url: "http://t.cn/A6N1B8c9",
    },
    {
      title: "2023年5月16日 晨读",
      url: "http://t.cn/A6NBsjgM",
    },
    {
      title: "2023年5月17日 晨读",
      url: "http://t.cn/A6NdxIrc",
    },
    {
      title: "2023年5月18日 晨读",
      url: "http://t.cn/A6NgjpS1",
    },
    {
      title: "2023年5月19日 晨读",
      url: "http://t.cn/A6NeFJaa",
    },
    {
      title: "块1-5：亲情、青春、劳动",
      url: "http://t.cn/A6NDWcvo",
    },
    {
      title: "2023年5月22日 晨读",
      url: "http://t.cn/A6Nsx80b",
    },
    {
      title: "2023年5月23日 晨读",
      url: "http://t.cn/A6pvlwye",
    },
    {
      title: "块6-11：亲情、劳动、望乡",
      url: "http://t.cn/A6pPNI3N",
    },
    {
      title: "2023年5月24日 晨读",
      url: "http://t.cn/A6pPrj0r",
    },
    {
      title: "2023年5月25日 晨读",
      url: "http://t.cn/A6p7brBG",
    },
    {
      title: "2023年5月26日 晨读",
      url: "http://t.cn/A6pz94Ec",
    },
    {
      title: "块12-16：青春、工匠、文化",
      url: "http://t.cn/A6pzlANo",
    },
    {
      title: "2023年5月29日 晨读",
      url: "http://t.cn/A6p2Udtn",
    },
    {
      title: "2023年5月30日 晨读",
      url: "http://t.cn/A6pL92HO",
    },
    {
      title: "块17-22：亲情、文化",
      url: "http://t.cn/A6pyaB0H",
    },
    {
      title: "2023年6月1日 晨读",
      url: "http://t.cn/A6p45gwk",
    },
    {
      title: "2023年6月2日 晨读",
      url: "http://t.cn/A6pbOCl3",
    },
    {
      title: "块23-28：劳动、文化",
      url: "http://t.cn/A6pbQbsv",
    },
    {
      title: "2023年6月5日 晨读",
      url: "http://t.cn/A6ptUx0K",
    },
    {
      title: "块29-34：亲情、青春",
      url: "http://t.cn/A6pc27UM",
    },
    {
      title: "2023年6月7日 晨读",
      url: "http://t.cn/A6pVdUCI",
    },
    {
      title: "2023年6月8日 晨读",
      url: "http://t.cn/A6pIcEYB",
    },
    {
      title: "块35-41：青春",
      url: "http://t.cn/A6pIiEhB",
    },
    {
      title: "块42-47：青春",
      url: "http://t.cn/A6pXeLh6",
    },
    {
      title: "2023年6月13日 晨读",
      url: "http://t.cn/A6paVUdc",
    },
    {
      title: "语音、语法、语汇",
      url: "http://t.cn/A6pS5Q1E",
    },
    {
      title: "2023年6月14日 晨读",
      url: "http://t.cn/A6pSY28R",
    },
    {
      title: "后记：实用技巧与写作的未来",
      url: "http://t.cn/A6pojysI",
    },
    {
      title: "块48-53：古人、文化",
      url: "http://t.cn/A6pKbZXh",
    },
    {
      title: "块54-60：古人、文化",
      url: "http://t.cn/A6p9ANFu",
    },
    {
      title: "2023年6月16日 晨读",
      url: "http://t.cn/A6p9NFc2",
    },
    {
      title: "后记：《积木拓写包》服用说明",
      url: "http://t.cn/A6p9T4cJ",
    },
    {
      title: "2023年6月19日 晨读",
      url: "http://t.cn/A6p09upR",
    },
    {
      title: "2023年6月20日 晨读",
      url: "http://t.cn/A6pWLxPM",
    },
    {
      title: "2023年6月21日 晨读",
      url: "http://t.cn/A6pl0VNu",
    },
    {
      title: "2023年6月22日 晨读",
      url: "http://t.cn/A6pjsSxK",
    },
    {
      title: "2023年6月23日 晨读",
      url: "http://t.cn/A6pT44H8",
    },
    {
      title: "2023年6月26日 晨读",
      url: "http://t.cn/A6pRzhGl",
    },
    {
      title: "2023年6月27日 晨读",
      url: "http://t.cn/A6pEamTz",
    },
    {
      title: "2023年6月28日 晨读",
      url: "http://t.cn/A6pn17Kk",
    },
    {
      title: "2023年6月29日 晨读",
      url: "http://t.cn/A6puGNkw",
    },
    {
      title: "2023年6月30日 晨读",
      url: "http://t.cn/A6p3Q7l7",
    },
    {
      title: "2023年7月3日 晨读",
      url: "http://t.cn/A6pdpC00",
    },
    {
      title: "L1-1 语言的情感磁极①",
      url: "http://t.cn/A6pgNtbW",
    },
    {
      title: "2023年7月4日 晨读",
      url: "http://t.cn/A6pgepSF",
    },
    {
      title: "L1-2 语言的情感磁极②",
      url: "http://t.cn/A6pedvx5",
    },
    {
      title: "2023年7月5日 晨读",
      url: "http://t.cn/A6pDtP1D",
    },
    {
      title: "2023年7月6日 晨读",
      url: "http://t.cn/A6pkTvUl",
    },
    {
      title: "L1-3 语言的情感磁极③",
      url: "http://t.cn/A6pkE9KY",
    },
    {
      title: "2023年7月7日 晨读",
      url: "http://t.cn/A6ps76mI",
    },
    {
      title: "语言的情感磁极 参考答案",
      url: "http://t.cn/A6ps2gjk",
    },
    {
      title: "2023年7月10日 晨读",
      url: "http://t.cn/A60hgsDJ",
    },
    {
      title: "2023年7月11日 晨读",
      url: "http://t.cn/A60zMlyA",
    },
    {
      title: "L2-1 展示，而非告知①",
      url: "http://t.cn/A60zXRJe",
    },
    {
      title: "2023年7月12日 晨读",
      url: "http://t.cn/A60Z1MTb",
    },
    {
      title: "L2-2 展示，而非告知②",
      url: "http://t.cn/A60ZepKu",
    },
    {
      title: "2023年7月13日 晨读",
      url: "http://t.cn/A60AqLYz",
    },
    {
      title: "L2-3 展示，而非告知③",
      url: "http://t.cn/A60AfboL",
    },
    {
      title: "2023年7月14日 晨读",
      url: "http://t.cn/A602Wto6",
    },
    {
      title: "L2-4 展示，而非告知④",
      url: "http://t.cn/A60LarXV",
    },
    {
      title: "2023年7月15日 晨读",
      url: "http://t.cn/A60yhwgh",
    },
    {
      title: "展示，而非告知 参考答案",
      url: "http://t.cn/A60ywJYt",
    },
    {
      title: "2023年7月16日 晨读",
      url: "http://t.cn/A60UcDpX",
    },
    {
      title: "2023年7月17日 晨读",
      url: "http://t.cn/A604N7qO",
    },
    {
      title: "L3-1 什么引起了皮肤的感觉？①",
      url: "http://t.cn/A60bKcTY",
    },
    {
      title: "2023年7月18日 晨读",
      url: "http://t.cn/A60bFxFR",
    },
    {
      title: "2023年7月19日 晨读",
      url: "http://t.cn/A60qIuSL",
    },
    {
      title: "L3-2 什么引起了皮肤的感觉？②",
      url: "http://t.cn/A60qXAB7",
    },
    {
      title: "2023年7月20日 晨读",
      url: "http://t.cn/A605uGyW",
    },
    {
      title: "什么引起了皮肤的感觉？ 参考答案",
      url: "http://t.cn/A605gzYq",
    },
    {
      title: "2023年7月21日 晨读",
      url: "http://t.cn/A60cI4Qs",
    },
    {
      title: "2023年7月22日 晨读",
      url: "http://t.cn/A60V1MnL",
    },
    {
      title: "2023年7月23日 晨读",
      url: "http://t.cn/A60IGUcU",
    },
    {
      title: "L4-1 听，一场视觉的盛宴①",
      url: "http://t.cn/A60MllSd",
    },
    {
      title: "2023年7月25日 晨读",
      url: "http://t.cn/A60Jvjfn",
    },
    {
      title: "L4-2 听，一场视觉的盛宴②",
      url: "http://t.cn/A60Jwzyt",
    },
    {
      title: "2023年7月26日 晨读",
      url: "http://t.cn/A60ipNzW",
    },
    {
      title: "听，一场视觉的盛宴 参考答案",
      url: "http://t.cn/A60iYxlG",
    },
    {
      title: "2023年7月31日 晨读",
      url: "http://t.cn/A609ekDd",
    },
    {
      title: "L5-1 嗅与尝①",
      url: "http://t.cn/A60CPOYQ",
    },
    {
      title: "2023年8月1日 晨读",
      url: "http://t.cn/A60NSoSP",
    },
    {
      title: "L5-2 嗅与尝②",
      url: "http://t.cn/A60NNmeo",
    },
    {
      title: "2023年8月2日 晨读",
      url: "http://t.cn/A60pk3ZN",
    },
    {
      title: "嗅与尝 参考答案",
      url: "http://t.cn/A60075k7",
    },
    {
      title: "2023年8月3日 晨读",
      url: "http://t.cn/A60Oozws",
    },
    {
      title: "阶段挑战① 对“具体”的理解",
      url: "http://t.cn/A60OpSXK",
    },
    {
      title: "2023年8月4日 晨读",
      url: "http://t.cn/A60lvYVy",
    },
    {
      title: "L6-1 视觉描写=名词们的组合①",
      url: "http://t.cn/A60lwzZk",
    },
    {
      title: "2023年8月5日 晨读",
      url: "http://t.cn/A60jloLP",
    },
    {
      title: "2023年8月7日 晨读",
      url: "http://t.cn/A60HK9VN",
    },
    {
      title: "L6-2 视觉描写=名词们的组合②",
      url: "http://t.cn/A60HOcuB",
    },
    {
      title: "2023年8月8日 晨读",
      url: "http://t.cn/A608zYIn",
    },
    {
      title: "L6-3 视觉描写=名词们的组合③",
      url: "http://t.cn/A608yU0J",
    },
    {
      title: "2023年8月9日 晨读",
      url: "http://t.cn/A60RWsph",
    },
    {
      title: "L6-4 视觉描写=名词们的组合④",
      url: "http://t.cn/A60RQd5G",
    },
    {
      title: "2023年8月10日 晨读",
      url: "http://t.cn/A60nbpTk",
    },
    {
      title: "视觉描写=名词们的组合 参考答案①",
      url: "http://t.cn/A60nVJU0",
    },
    {
      title: "2023年8月11日 晨读",
      url: "http://t.cn/A60mEGVI",
    },
    {
      title: "L6-5 视觉描写=名词们的组合⑤",
      url: "http://t.cn/A60m10Sf",
    },
    {
      title: "2023年8月14日 晨读",
      url: "http://t.cn/A60ry2Ep",
    },
    {
      title: "L6-6 视觉描写=名词们的组合⑥",
      url: "http://t.cn/A60rqjIt",
    },
    {
      title: "2023年8月15日 晨读",
      url: "http://t.cn/A60dOcaR",
    },
    {
      title: "视觉描写=名词们的组合 参考答案②",
      url: "http://t.cn/A60dTHYV",
    },
    {
      title: "2023年8月16日 晨读",
      url: "http://t.cn/A60ePo1z",
    },
    {
      title: "L3-3 什么引起了皮肤的感觉？③",
      url: "http://t.cn/A60eweyZ",
    },
    {
      title: "2023年8月17日 晨读",
      url: "http://t.cn/A60DaMBW",
    },
    {
      title: "L4-3 听，一场视觉的盛宴③",
      url: "http://t.cn/A60DCnz1",
    },
    {
      title: "2023年8月18日 晨读",
      url: "http://t.cn/A60kFPM8",
    },
    {
      title: "L5-3 嗅与尝③",
      url: "http://t.cn/A60F7aK3",
    },
    {
      title: "2023年8月21日 晨读",
      url: "http://t.cn/A6Oh27vN",
    },
    {
      title: "L3-3 L4-3 L5-3 参考答案",
      url: "http://t.cn/A6Oh4rkq",
    },
    {
      title: "2023年8月22日 晨读",
      url: "http://t.cn/A6O7pbx7",
    },
    {
      title: "阶段挑战② 一段描写",
      url: "http://t.cn/A6O7jXfV",
    },
    {
      title: "2023年8月23日 晨读",
      url: "http://t.cn/A6OzkBpV",
    },
    {
      title: "L7-1 视角与视点①",
      url: "http://t.cn/A6OZhLX8",
    },
    {
      title: "2023年8月24日 晨读",
      url: "http://t.cn/A6OwZXbW",
    },
    {
      title: "L7-2 视角与视点②",
      url: "http://t.cn/A6OwLW9I",
    },
    {
      title: "2023年8月25日 晨读",
      url: "http://t.cn/A6Oyjk8X",
    },
    {
      title: "2023年8月28日晨读",
      url: "http://t.cn/A6OyjsGr",
    },
    {
      title: "L7-3 视角与视点③",
      url: "http://t.cn/A6Oy8zsN",
    },
    {
      title: "2023年8月29日 晨读",
      url: "http://t.cn/A6OUdFzT",
    },
    {
      title: "视角与视点 参考答案",
      url: "http://t.cn/A6OUFyae",
    },
    {
      title: "2023年8月30日 晨读",
      url: "http://t.cn/A6O4sqga",
    },
    {
      title: "L8-1 最小努力法则①",
      url: "http://t.cn/A6Ob7TG3",
    },
    {
      title: "2023年8月31日 晨读",
      url: "http://t.cn/A6OGzTYG",
    },
    {
      title: "L8-2 最小努力法则②",
      url: "http://t.cn/A6OG21Jk",
    },
    {
      title: "2023年9月1日 晨读",
      url: "http://t.cn/A6Oq2pQE",
    },
    {
      title: "L8-3 最小努力法则③",
      url: "http://t.cn/A6Oq4q7Y",
    },
    {
      title: "2023年9月4日 晨读",
      url: "http://t.cn/A6OcvFz3",
    },
    {
      title: "最小努力法则 参考答案",
      url: "http://t.cn/A6OczmqX",
    },
    {
      title: "2023年9月5日 晨读",
      url: "http://t.cn/A6OVAfJA",
    },
    {
      title: "L9-1 需要、想要①",
      url: "http://t.cn/A6OV40Ut",
    },
    {
      title: "2023年9月6日 晨读",
      url: "http://t.cn/A6Ofx7vE",
    },
    {
      title: "L9-2 需要、想要②",
      url: "http://t.cn/A6OfaHRv",
    },
    {
      title: "2023年9月7日 晨读",
      url: "http://t.cn/A6OIRlxm",
    },
    {
      title: "L9-3 需要、想要③",
      url: "http://t.cn/A6OI1AFh",
    },
    {
      title: "2023年9月8日 晨读",
      url: "http://t.cn/A6Ox2qmw",
    },
    {
      title: "需要、想要 参考答案",
      url: "http://t.cn/A6OxGw9u",
    },
    {
      title: "2023年9月11日 晨读",
      url: "http://t.cn/A6O6ryKe",
    },
    {
      title: "L10-1 叙事=指数函数①",
      url: "http://t.cn/A6O6katP",
    },
    {
      title: "2023年9月12日 晨读",
      url: "http://t.cn/A6Oa410h",
    },
    {
      title: "L10-2 叙事=指数函数②",
      url: "http://t.cn/A6Oac2ei",
    },
    {
      title: "2023年9月13日 晨读",
      url: "http://t.cn/A6OS6RaI",
    },
    {
      title: "L10-3 叙事=指数函数③",
      url: "http://t.cn/A6OoVLTh",
    },
    {
      title: "2023年9月14日 晨读",
      url: "http://t.cn/A6OoTBsm",
    },
    {
      title: "L10-4 叙事=指数函数④",
      url: "http://t.cn/A6OontFY",
    },
    {
      title: "2023年9月15日 晨读",
      url: "http://t.cn/A6O97Ed8",
    },
    {
      title: "叙事=指数函数 参考答案①-④",
      url: "http://t.cn/A6O9LAKo",
    },
    {
      title: "2023年9月18日 晨读",
      url: "http://t.cn/A6Op1gke",
    },
    {
      title: "L10-5 叙事=指数函数⑤",
      url: "http://t.cn/A6Op1sBg",
    },
    {
      title: "2023年9月19日 晨读",
      url: "http://t.cn/A6OOqyZ9",
    },
    {
      title: "L10-6 叙事=指数函数⑥",
      url: "http://t.cn/A6OOIWqk",
    },
    {
      title: "2023年9月20日 晨读",
      url: "http://t.cn/A6OlzNDL",
    },
    {
      title: "L10-7 需要、想要④",
      url: "http://t.cn/A6Ol40lm",
    },
    {
      title: "2023年9月21日 晨读",
      url: "http://t.cn/A6OjxL6J",
    },
    {
      title: "L10-8 视角与视点④",
      url: "http://t.cn/A6Ojapyf",
    },
    {
      title: "2023年9月22日 晨读",
      url: "http://t.cn/A6OYRyG2",
    },
    {
      title: "L10-5~L10-8 参考答案",
      url: "http://t.cn/A6OY3SsY",
    },
    {
      title: "2023年9月25日 晨读",
      url: "http://t.cn/A6O8aUyB",
    },
    {
      title: "阶段挑战③ 简易叙事弧",
      url: "http://t.cn/A6O8CisT",
    },
    {
      title: "2023年9月26日 晨读",
      url: "http://t.cn/A6ORTTFO",
    },
    {
      title: "L11-1 示现！①",
      url: "http://t.cn/A6OREnCc",
    },
    {
      title: "2023年9月27日 晨读",
      url: "http://t.cn/A6OnPbwW",
    },
    {
      title: "L11-2 示现！②",
      url: "http://t.cn/A6OnwKPF",
    },
    {
      title: "2023年9月28日 晨读",
      url: "http://t.cn/A6OmtIVp",
    },
    {
      title: "L11-3 示现！③",
      url: "http://t.cn/A6OmMYJ1",
    },
    {
      title: "2023年9月29日 晨读",
      url: "http://t.cn/A6OuQikK",
    },
    {
      title: "示现 参考答案",
      url: "http://t.cn/A6OumWMD",
    },
    {
      title: "2023年10月9日 晨读",
      url: "http://t.cn/A6WvHT6I",
    },
    {
      title: "L12-1 语言的情感磁极④",
      url: "http://t.cn/A6WvnILY",
    },
    {
      title: "2023年10月10日 晨读",
      url: "http://t.cn/A6WP1ohi",
    },
    {
      title: "L12-2 比喻①",
      url: "http://t.cn/A6WPeLBo",
    },
    {
      title: "2023年10月11日 晨读",
      url: "http://t.cn/A6WhFCH5",
    },
    {
      title: "L12-3 比喻②",
      url: "http://t.cn/A6W776VR",
    },
    {
      title: "2023年10月12日 晨读",
      url: "http://t.cn/A6WzAseO",
    },
    {
      title: "L12-4 比喻③",
      url: "http://t.cn/A6Wz4TOZ",
    },
    {
      title: "2023年10月13日 晨读",
      url: "http://t.cn/A6WZIowr",
    },
    {
      title: "L12-1~L12-4 参考答案",
      url: "http://t.cn/A6WZXN2T",
    },
    {
      title: "2023年10月16日 晨读",
      url: "http://t.cn/A6W212ht",
    },
    {
      title: "L13-1 拟人①",
      url: "http://t.cn/A6W2e9yr",
    },
    {
      title: "2023年10月17日 晨读",
      url: "http://t.cn/A6Wy7ibu",
    },
    {
      title: "L13-2 拟人②",
      url: "http://t.cn/A6Wy25UT",
    },
    {
      title: "2023年10月18日 晨读",
      url: "http://t.cn/A6WUb8vE",
    },
    {
      title: "拟人 参考答案",
      url: "http://t.cn/A6WUcEQu",
    },
    {
      title: "2023年10月19日 晨读",
      url: "http://t.cn/A6W4aVzW",
    },
    {
      title: "阶段挑战④ 即兴离调",
      url: "http://t.cn/A6W4CJPu",
    },
    {
      title: "2023年10月20 日 晨读",
      url: "http://t.cn/A6WbEIN8",
    },
    {
      title: "中考作文题目：照亮①",
      url: "http://t.cn/A6WGOF9G",
    },
    {
      title: "2023年10月23日 晨读",
      url: "http://t.cn/A6WtqvQ7",
    },
    {
      title: "中考作文题目：照亮②",
      url: "http://t.cn/A6WcZSIk",
    },
    {
      title: "2023年10月24日 晨读",
      url: "http://t.cn/A6Wc0Tpy",
    },
    {
      title: "中考作文题目：照亮③",
      url: "http://t.cn/A6WVx9lM",
    },
    {
      title: "2023年10月25日 晨读",
      url: "http://t.cn/A6WV3hAu",
    },
    {
      title: "2023年10月26日 晨读",
      url: "http://t.cn/A6WIhgdD",
    },
    {
      title: "L14-1 横向结构①",
      url: "http://t.cn/A6WIUvYU",
    },
    {
      title: "小孩子该如何写日记",
      url: "http://t.cn/A6WIcF9b",
    },
    {
      title: "2023年10月27日 晨读",
      url: "http://t.cn/A6WMqI2r",
    },
    {
      title: "L14-2 横向结构②",
      url: "http://t.cn/A6WMxk97",
    },
    {
      title: "2023年10月30日 晨读",
      url: "http://t.cn/A6WipxGC",
    },
    {
      title: "L14-3 横向结构③",
      url: "http://t.cn/A6WiH2N2",
    },
    {
      title: "2023年10月31日 晨读",
      url: "http://t.cn/A6W61F6m",
    },
    {
      title: "横向结构 参考答案",
      url: "http://t.cn/A6W6FnPP",
    },
    {
      title: "2023年11月1日 晨读",
      url: "http://t.cn/A6WaALwV",
    },
    {
      title: "L15-1 视角与视点④",
      url: "http://t.cn/A6WaqyOe",
    },
    {
      title: "2023年11月2日 晨读",
      url: "http://t.cn/A6WSXqo9",
    },
    {
      title: "L15-2 视角与视点⑤",
      url: "http://t.cn/A6WSNShk",
    },
    {
      title: "2023年11月3日 晨读",
      url: "http://t.cn/A6WoOpIR",
    },
    {
      title: "视角与视点 参考答案",
      url: "http://t.cn/A6Wo8J8G",
    },
    {
      title: "2023年11月6日 晨读",
      url: "http://t.cn/A6WNb19r",
    },
    {
      title: "L16-1 写人的技巧①",
      url: "http://t.cn/A6WNb1Qc",
    },
    {
      title: "2023年11月7日 晨读",
      url: "http://t.cn/A6WpXOZa",
    },
    {
      title: "L16-2 写人的技巧②",
      url: "http://t.cn/A6WpXnUW",
    },
    {
      title: "2023年11月8日 晨读",
      url: "http://t.cn/A6W08hNF",
    },
    {
      title: "L16-3 写人的技巧③",
      url: "http://t.cn/A6W08y2U",
    },
  ];
}
