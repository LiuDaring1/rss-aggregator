import { load } from 'cheerio';
import pMap from 'p-map';

import type { Route } from '@/types';
import cache from '@/utils/cache';
import got from '@/utils/got';
import { parseDate } from '@/utils/parse-date';
import timezone from '@/utils/timezone';

const rootUrl = 'https://guancha.gmw.cn';

export const route: Route = {
    path: '/guancha/:node?',
    categories: ['traditional-media'],
    example: '/gmw/guancha/11273',
    parameters: { node: '栏目节点 id，可在栏目页 URL 中找到，如 node_11273 即「光明网评论员」' },
    features: {
        requireConfig: false,
        requirePuppeteer: false,
        antiCrawler: false,
        supportBT: false,
        supportPodcast: false,
        supportScihub: false,
    },
    name: '评论频道栏目',
    maintainers: ['nczitzk'],
    radar: [
        {
            source: ['guancha.gmw.cn/node_:node'],
            target: '/gmw/guancha/:node',
        },
    ],
    handler,
};

async function handler(ctx) {
    const node = ctx.req.param('node') ?? '11273';
    const url = `${rootUrl}/node_${node}.htm`;

    const { data: response } = await got(url);
    const $ = load(response);

    const list = $('ul.content_left_main li')
        .toArray()
        .map((item) => {
            const $item = $(item);
            const link = new URL($item.find('p.main_title a').attr('href') ?? '', url).href;
            const date = link.match(/\/(\d{4}-\d{2})\//)?.[1] || '';
            return {
                title: $item.find('p.main_title a').text().trim(),
                link,
                pubDate: date ? timezone(parseDate(`${date}-01`), 8) : null,
            };
        });

    const items = await pMap(
        list,
        (item) =>
            cache.tryGet(item.link, async () => {
                const { data: detailResponse } = await got(item.link);
                const $detail = load(detailResponse);

                return {
                    ...item,
                    title: $detail('h1.u-title').text().trim() || item.title,
                    pubDate: timezone(parseDate($detail('span#articlePubTime').text().trim()), 8) || item.pubDate,
                    description: $detail('div.u-mainText').html() ?? '',
                };
            }),
        { concurrency: 3 }
    );

    return {
        title: $('title').text(),
        link: url,
        item: items,
    };
}
