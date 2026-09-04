import { load } from 'cheerio';
import pMap from 'p-map';

import type { Route } from '@/types';
import ofetch from '@/utils/ofetch';

import { fetchArticle } from './utils';

export const route: Route = {
    path: '/kuaiping',
    categories: ['traditional-media'],
    example: '/bjnews/kuaiping',
    parameters: { limit: '条数，默认 20' },
    features: {},
    radar: [
        {
            source: ['www.bjnews.com.cn/point'],
        },
    ],
    name: '快评·风向标',
    maintainers: ['RSS订阅-zcode'],
    handler,
    url: 'www.bjnews.com.cn',
};

async function handler(ctx) {
    // 2026-09 起源站（阿里云 WAF）会以 405 拦截头部不全的请求（上游 /cat/point/1.html 旧路径也被封），
    // 必须带 Referer 等完整浏览器头；栏目页迁移为 /point
    const url = 'https://www.bjnews.com.cn/point';
    const res = await ofetch(url, {
        headers: {
            Referer: 'https://www.bjnews.com.cn/',
            Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        },
    });
    const $ = load(res);
    const list = $('#waterfall-container .pin_demo > a')
        .toArray()
        .slice(0, ctx.req.query('limit') ? Number.parseInt(ctx.req.query('limit')) : 20)
        .map((a) => ({
            title: $(a).text(),
            link: $(a).attr('href'),
        }));

    const out = await pMap(
        list,
        async (item) => {
            try {
                return await fetchArticle(item);
            } catch {
                // 单篇详情被源站 WAF 拦截时降级：只出标题+链接，不让整条路由 503；
                // 拦截通常几分钟内解除，下次路由刷新会重取并补全日期与摘要
                return { ...item, pubDate: undefined };
            }
        },
        { concurrency: 2 }
    );
    return {
        title: '新京报 - 快评·风向标',
        link: url,
        item: out,
    };
}
