% rebase('base.tpl', base_vars=base_vars)
<h1>{{base_vars.title}}</h1>
% if next_page_url:
<div class="d-flex justify-content-center">
<ul class="pagination pagination-lg justify-content-end">
    <li class="page-item"><a class="page-link active" href="{{next_page_url}}">More Entries &raquo;</a></li>
</ul>
</div>
% end
<div class="row row-cols-auto g-3 justify-content-center">
% for entry in entries:
<div class="col">
<div class="card" style="width: 18rem;">
    <div class="card-header"><a href="{{entry.url}}" role="button">{{entry.entry_id}}</a> <span class="badge rounded-pill bg-primary">{{entry.blob_count}}</span></div>
    % if entry.preview_url:
    <a href="{{entry.preview_url}}"><img src="{{entry.preview_url}}" class="card-img-top"></a>
    % end
    <div class="card-body">
    % for tag in entry.tags:
    <a class="btn btn-primary btn-sm my-1" href="#" role="button">{{tag.value}}</a>
    % end
    </div>
</div>
</div>
% end
</div>
% if next_page_url:
<div class="d-flex justify-content-center">
<ul class="pagination pagination-lg justify-content-end">
    <li class="page-item"><a class="page-link active" href="{{next_page_url}}">More Entries &raquo;</a></li>
</ul>
</div>
% end
