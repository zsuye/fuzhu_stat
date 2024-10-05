// async function allUrlForOnePage(page) {
//   let res = await fetch(
//     `https://vipclub.weibo.com/aj/vmember/gfcontent?page=${page}&type=1&cid=&vuid=5917804563&sort=desc&page_size=8&weibo_client_from=&_lid=36385067998501011`
//   );
//   res = await res.json();
//   return res.data.list
//     .filter((x) => x.text_raw)
//     .map((x) => x.text_raw)
//     .map((x) => /发布了头条文章：《(.+)》.*(http:\/\/t.cn\/\w+)/.exec(x))
//     .filter((x) => x)
//     .map((x) => ({ title: x[1], url: x[2] }));
// }
async function allUrlForOnePage(page) {
  let res = await fetch(
    `https://vipclub.weibo.com/aj/vmember/gfcontent?page=${page}&type=1&cid=&vuid=5917804563&sort=desc&page_size=8&weibo_client_from=&_lid=36385067998501011`
  );
  res = await res.json();
  return res.data.list.map((x) => ({
    title: x.title,
    url: "https://weibo.com/ttarticle/p/show?id=" + /:(.+)/.exec(x.oid)[1],
  }));
}
function sleep(timeout) {
  return new Promise((r) => setTimeout(r, timeout));
}
async function allUrl(maxPage = 20, minPage = 1) {
  const all = [];
  for (let page = minPage; page <= maxPage; page++) {
    console.log("page " + page);
    const list = await allUrlForOnePage(page);
    all.push(...list);
    await sleep(5000);
  }
  return all.reverse();
}
