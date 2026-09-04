import { load } from 'cheerio';
import iconv from 'iconv-lite';
import pMap from 'p-map';

import type { Route } from '@/types';
import cache from '@/utils/cache';
import got from '@/utils/got';
import { parseDate } from '@/utils/parse-date';
import timezone from '@/utils/timezone';

const rootUrl = 'https://pinglun.youth.cn';

export const route: Route = {
    path: '/pinglun/:cat?',
    categories: ['traditional-media'],
    example: '/youth/pinglun/wztt',
    parameters: { cat: '评论频道栏目路径，默认为 `wztt`，即热点' },
    features: {
        requireConfig: false,
        requirePuppeteer: false,
        antiCrawler: false,
        supportBT: false,
        supportPodcast: false,
        supportScihub: false,
    },
    name: '评论频道',
    maintainers: ['nczitzk'],
    radar: [
        {
            source: ['pinglun.youth.cn/:cat'],
            target: '/youth/pinglun/:cat',
        },
    ],
    handler,
};

async function handler(ctx) {
    const cat = ctx.req.param('cat') ?? 'wztt';
    const url = `${rootUrl}/${cat}/`;

    const { data: response } = await got(url, {
        responseType: 'buffer',
    });
    const $ = load(iconv.decode(response, 'gbk'));

    const list = $('ul li div.title_txt')
        .toArray()
        .slice(0, ctx.req.query('limit') ? Number.parseInt(ctx.req.query('limit')) : 30)
        .map((item) => {
            const $item = $(item);
            const link = new URL($item.find('p.title a').attr('href') ?? '', url).href;
            return {
                title: $item.find('p.title a').text().trim(),
                link,
                pubDate: timezone(parseDate($item.find('span.date').text().trim()), 8),
            };
        });

    const items = await pMap(
        list,
        (item) =>
            cache.tryGet(item.link, async () => {
                const { data: detailResponse } = await got(item.link, {
                    responseType: 'buffer',
                });
                const $detail = load(iconv.decode(detailResponse, 'gbk'));

                const pwz = $detail('p.pwz').text().trim();
                const pubTime = pwz.match(/发稿时间：([\d-]+ [\d:]+)/)?.[1];
                const author = pwz.match(/作者：(\S+)/)?.[1];

                return {
                    ...item,
                    title: $detail('p.pbt').text().trim() || item.title,
                    author: author || '',
                    pubDate: pubTime ? timezone(parseDate(pubTime), 8) : item.pubDate,
                    description: $detail('div.TRS_Editor').html() ?? '',
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
