% rebase('base.tpl', base_vars=base_vars)
<div class="d-flex justify-content-center">
<ul class="list-group list-group-flush">
    <li class="list-group-item d-flex justify-content-between align-items-center">
        <h6 class="mx-1">Total</h6>
        <span class="badge bg-primary rounded-pill">{{count}}</span>
    </li>
    % for state, state_count in count_by_state:
    <li class="list-group-item d-flex justify-content-between align-items-center">
        <div class="mx-1">{{state}}</div>
        <span class="badge bg-primary rounded-pill">{{state_count}}</span>
    </li>
    % end
</ul>
</div>
<div class="row">
<div class="col-4"><h6>Ingestions</h6></div>
<div class="col-8"><h6>Downloads</h6></div>
<div class="col-4">
<div class="list-group" id="list-tab" role="tablist">
    % for idx, ingestion in enumerate(ingestions):
    <a class="list-group-item list-group-item-action{{' active' if idx == 0 else ''}}" id="{{id(ingestion)}}-list" data-bs-toggle="list" href="#{{id(ingestion)}}" role="tab" aria-controls="list-profile">
    <div class="d-flex w-100 justify-content-between">
        <h5 class="mb-1">{{ingestion.entry_id}}</h5>
        <small>{{ingestion.state}}</small>
    </div>
    <div class="d-flex w-100 justify-content-between">
        <small>{{ingestion.library_id}}</small>
        <span class="badge bg-primary rounded-pill">{{len(ingestion.downloads)}}</span>
    </div>
    </a>
    % end
</div>
</div>
<div class="col-8">
<div class="tab-content" id="nav-tabContent">
    % for idx, ingestion in enumerate(ingestions):
    <div class="tab-pane fade{{' show active' if idx == 0 else ''}}" id="{{id(ingestion)}}" role="tabpanel" aria-labelledby="{{id(ingestion)}}-list">
        % for dl in ingestion.downloads:
        <div class="overflow-hidden text-nowrap"><small><a href="{{dl.url}}">{{dl.url}}</a></small></div>
        <div class="progress my-1">
            <div class="progress-bar {{dl.progress_class}}" role="progressbar" style="width: {{dl.percent_complete}}%;" aria-valuenow="{{dl.percent_complete}}" aria-valuemin="0" aria-valuemax="100">{{dl.summary}}</div>
        </div>
        % end
    </div>
    % end
</div>
</div>
</div>