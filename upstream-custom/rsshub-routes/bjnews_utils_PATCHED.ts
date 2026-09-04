import { load } from 'cheerio';

import cache from '@/utils/cache';
import ofetch from '@/utils/ofetch';
import { parseDate } from '@/utils/parse-date';
import timezone from '@/utils/timezone';

export function fetchArticle(item) {
    return cache.tryGet(item.link, async () => {
        // 2026-09 起源站阿里云 WAF 会 405 掉头部不全的请求，详情页也需要完整浏览器头
        const responses = await ofetch(item.link, {
            headers: {
                Referer: 'https://www.bjnews.com.cn/',
                Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9',
            },
        });
        const $d = load(responses);
        // $d('img').each((i, e) => $(e).attr('referrerpolicy', 'no-referrer'));

        item.pubDate = timezone(parseDate($d('.left-info .timer').text()), 8);
        item.author = $d('.left-info .reporter').text();
        item.description = $d('#contentStr').html();

        return item;
    });
}
