# unbound

Pythond module for ganglia. Reads stats from `unbound-control stats`.

http://unbound.net/documentation/unbound-control.html

## privileges

The ganglia user needs to execute the unbound-control stats command, so it's
probably necessary to add this to your sudoers file:

	ganglia ALL=(root) NOPASSWD: /usr/sbin/unbound-control stats

## stats

* unbound_queries

  number of queries received

* unbound_cachehits

  number of queries that were successfully answered using a cache lookup

* unbound_cachemiss

  number of queries that needed recursive processing

* unbound_prefetch

  number  of  cache prefetches performed.  This number is included
  in cachehits, as the original query had the unprefetched  answer
  from  cache, and resulted in recursive processing, taking a slot
  in the requestlist.  Not part of the  recursivereplies  (or  the
  histogram thereof) or cachemiss, as a cache response was sent.

* unbound_recursivereplies

  The number of replies sent to queries that needed recursive pro-
  cessing. Could be smaller than threadX.num.cachemiss if  due  to
  timeouts no replies were sent for some queries.

* unbound_requestlist_avg

  The  average  number  of requests in the internal recursive pro-
  cessing request list on insert of a new incoming recursive  pro-
  cessing query.

* unbound_requestlist_max

  Maximum  size  attained  by  the  internal  recursive processing
  request list.

* unbound_requestlist_overwritten

  Number of requests in the request list that were overwritten  by
  newer  entries. This happens if there is a flood of queries that
  recursive processing and the server has a hard time.

* unbound_requestlist_exceeded

  Queries that were dropped because the  request  list  was  full.
  This  happens  if  a flood of queries need recursive processing,
  and the server can not keep up.

* unbound_requestlist_current_all

  Current size of the request list, includes internally  generated
  queries (such as priming queries and glue lookups).

* unbound_requestlist_current_user

  Current  size of the request list, only the requests from client
  queries.

* unbound_recursion_time_avg

  Average time it took to answer  queries  that  needed  recursive
  processing.  Note that queries that were answered from the cache
  are not in this average.

* unbound_recursion_time_median

  The median of the time it took to  answer  queries  that  needed
  recursive  processing.   The  median  means that 50% of the user
  queries were answered in less than this time.   Because  of  big
  outliers  (usually queries to non responsive servers), the aver-
  age can be bigger than the median.  This median has been  calcu-
  lated by interpolation from a histogram.
