<!DOCTYPE html>
<html lang="en">
    <head>
        <title>SBS2: {{base_vars.title}}</title>
        <meta charset="UTF-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-GLhlTQ8iRABdZLl6O3oVMWSktQOp6b7In1Zl3/Jr59b6EGGoI1aFkw7cmDA6j6gD" crossorigin="anonymous">
    </head>
    <body>
    <div class="container">
    <nav class="navbar navbar-expand-xl navbar-dark bg-dark">
      <div class="container-fluid">
        <a class="navbar-brand" href="#">SBS2</a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarSupportedContent" aria-controls="navbarSupportedContent" aria-expanded="false" aria-label="Toggle navigation">
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarSupportedContent">
          <ul class="navbar-nav me-auto mb-2 mb-lg-0">
          % for idx, item in enumerate(base_vars.nav_bar_items):
                % if type(item).__name__ == 'NavBarLink':
                    <li class="nav-item"><a class="nav-link" href="{{item.url}}">{{item.label}}</a></li>
                % end
                % if type(item).__name__ == 'NavBarDropDown':
                    <li class="nav-item dropdown">
                      <a class="nav-link dropdown-toggle" href="{{item.url}}" id="navbarDropdown{{idx}}" role="button" data-bs-toggle="dropdown">{{item.label}}</a>
                      <ul class="dropdown-menu">
                      % for link in item.sub_links:
                      <li><a class="dropdown-item" href="{{link.url}}">{{link.label}}</a></li>
                      % end
                      </ul>
                    </li>
                % end
          % end
        </div>
      </div>
    </nav>
    {{!base}}
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js" integrity="sha384-w76AqPfDkMBDXo30jS1Sgez6pr3x5MlQ1ZAGC+nuZB+EYdgRZgiwxhTBTkF7CXvN" crossorigin="anonymous"></script>
    </body>
</html>