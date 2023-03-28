% rebase('base.tpl', base_vars=base_vars)
<div class="d-flex justify-content-center">
<ul class="list-group list-group-flush">
% for library in libraries:
  <li class="list-group-item justify-content-between"><a href="{{library.url}}?sort=desc">{{library.library_id}}</a></br></li>
%end
</ul>
</div>

