% rebase('base.tpl', base_vars=base_vars)
<h1>{{base_vars.title}}</h1>
<h3>Metadata</h3>
<h5>Attributes</h5>
<table class="table table-borderless">
<tbody>
    % for attr in entry.attributes:
    <tr>
    <th scope="row">{{attr.key}}</th>
    <td>{{attr.value}}</td>
    </tr>
    % end
</tbody>
</table>
<h5>Tags</h5>
<div>
    % for tag in entry.tags:
    <a class="btn btn-primary" href="#" role="button">{{tag.value}}</a>
    % end
</div>
<h3>Blobs</h3>
<div class="row row-cols-auto g-3 justify-content-center">
% for blob in entry.blob_sequence:
<div class="col">
<div class="card" style="width: 18rem;">
    <div class="card-header"><a href="{{blob.url}}">{{blob.blob_id}}</a></div>
    % if blob.preview_url:
    <a href="{{blob.url}}"><img src="{{blob.preview_url}}" class="card-img-top"></a>
    % end
</div>
</div>
% end
</div>
