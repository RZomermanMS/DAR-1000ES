// Standalone C++17 router. All coordinates and dimensions are millimetres.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdio>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <locale>
#include <map>
#include <numeric>
#include <queue>
#include <random>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

namespace {
// Guard the .20 mm clearance against coordinate rounding on interchange.
constexpr double W = 100, H = 300, EDGE = .5, GAP = .202;
constexpr double GRID = .25, LAND = .8, TERMINAL = .875, WIRE = .55;
constexpr double EPS = 1e-8, INF = 1e30;
constexpr int NX = int(W / GRID) + 1, NY = int(H / GRID) + 1;
constexpr int BX = 50, BY = 150;

struct P {
    double x, y;
    P operator+(P b) const { return {x + b.x, y + b.y}; }
    P operator-(P b) const { return {x - b.x, y - b.y}; }
    P operator*(double f) const { return {x * f, y * f}; }
};
double dot(P a, P b) { return a.x * b.x + a.y * b.y; }
double cross(P a, P b) { return a.x * b.y - a.y * b.x; }
double sq(P a) { return dot(a, a); }
double distance(P a, P b) { return std::sqrt(sq(a - b)); }
P interpolate(P a, P b, double t) {
    const P p = a + (b - a) * t;
    return {std::round(p.x * 1e6) / 1e6, std::round(p.y * 1e6) / 1e6};
}

struct Box { double l, t, r, b; };
Box bounds(P a, P b, double r = 0) {
    return {std::min(a.x,b.x)-r, std::min(a.y,b.y)-r,
            std::max(a.x,b.x)+r, std::max(a.y,b.y)+r};
}
Box join(Box a, Box b) {
    return {std::min(a.l,b.l),std::min(a.t,b.t),std::max(a.r,b.r),std::max(a.b,b.b)};
}
bool overlaps(Box a, Box b) { return a.l <= b.r && a.r >= b.l && a.t <= b.b && a.b >= b.t; }
bool inside(P p, double r) {
    return p.x >= EDGE+r && p.y >= EDGE+r && p.x <= W-EDGE-r && p.y <= H-EDGE-r;
}
double pointLine(P p, P a, P b) {
    const P d = b-a;
    const double len = sq(d);
    if (len < EPS*EPS) return sq(p-a);
    return sq(p-(a+d*std::clamp(dot(p-a,d)/len, 0., 1.)));
}
double lineLine(P a, P b, P c, P d) {
    if (overlaps(bounds(a,b),bounds(c,d)) &&
        cross(b-a,c-a)*cross(b-a,d-a) <= 0 &&
        cross(d-c,a-c)*cross(d-c,b-c) <= 0) return 0;
    return std::min({pointLine(a,c,d), pointLine(b,c,d), pointLine(c,a,b), pointLine(d,a,b)});
}
double lineBox(P a, P b, Box q) {
    if (overlaps(bounds(a,a),q) || overlaps(bounds(b,b),q)) return 0;
    const P nw{q.l,q.t}, ne{q.r,q.t}, sw{q.l,q.b}, se{q.r,q.b};
    return std::min({lineLine(a,b,nw,ne),lineLine(a,b,ne,se),
                     lineLine(a,b,se,sw),lineLine(a,b,sw,nw)});
}

struct GridIndex {
    std::vector<std::vector<int>> buckets = std::vector<std::vector<int>>(BX*BY);
    template <class F> bool visit(Box b, F f) const {
        const auto clamp = [](double z, int n) { return int(std::clamp(z/2, 0., double(n-1))); };
        const int x0=clamp(b.l,BX), x1=clamp(b.r,BX), y0=clamp(b.t,BY), y1=clamp(b.b,BY);
        for (int y=y0; y<=y1; ++y) for (int x=x0; x<=x1; ++x)
            for (int k : buckets[y*BX+x]) if (!f(k)) return false;
        return true;
    }
    void add(Box b, int i) {
        const auto clamp = [](double z, int n) { return int(std::clamp(z/2, 0., double(n-1))); };
        for (int y=clamp(b.t,BY); y<=clamp(b.b,BY); ++y)
            for (int x=clamp(b.l,BX); x<=clamp(b.r,BX); ++x) buckets[y*BX+x].push_back(i);
    }
};

struct Pad { int net; P p; Box box; };
struct Route { int net; P a,b; bool bridge; };
struct Copper { int net; P a,b; double radius; Box box; bool pad; int track=-1; };
std::array<Box,3> envelope(P a,P b) {
    return {bounds(a,b,WIRE),bounds(a,a,TERMINAL),bounds(b,b,TERMINAL)};
}
bool bridgesOverlap(const Route& a,const Route& b) {
    for (Box x : envelope(a.a,a.b)) for (Box y : envelope(b.a,b.b))
        if (overlaps(x,y)) return true;
    return false;
}

struct Dsu {
    std::vector<int> p;
    explicit Dsu(int n) : p(n) { std::iota(p.begin(),p.end(),0); }
    int root(int i) { return p[i]==i ? i : p[i]=root(p[i]); }
    void unite(int i,int j) { p[root(i)]=root(j); }
};

struct World {
    std::vector<Pad> pads;
    std::vector<Box> blocks;
    std::vector<Route> routes;
    std::map<int,double> widths;
    std::map<int,std::pair<double,double>> channels;
    std::map<int,std::vector<int>> pins;
    std::vector<Copper> copper;
    std::vector<Box> top;
    GridIndex bottom, upper;
    double radius(int n) const {
        auto it=widths.find(n);
        return it==widths.end() ? .15 : it->second/2;
    }
    void index() {
        bottom=GridIndex{}; upper=GridIndex{};
        copper.clear(); top.clear();
        auto add=[&](Copper c) { bottom.add(c.box,int(copper.size())); copper.push_back(c); };
        auto block=[&](Box b) { upper.add(b,int(top.size())); top.push_back(b); };
        for (const Pad& p : pads) add({p.net,p.p,p.p,0,p.box,true});
        for (Box b : blocks) block(b);
        for (size_t i=0;i<routes.size();++i) {
            const Route& r=routes[i];
            if (r.bridge) {
                for (Box b : envelope(r.a,r.b)) block(b);
                for (P p : {r.a,r.b}) add({r.net,p,p,LAND,bounds(p,p,LAND),false});
            } else {
                double rad=radius(r.net);
                add({r.net,r.a,r.b,rad,bounds(r.a,r.b,rad),false,int(i)});
            }
        }
    }
    bool clear(int net, P a,P b,double r,std::map<int,int>* hits=nullptr,
               std::vector<int>* conflicts=nullptr,bool terminal=false) const {
        if (!inside(a,r) || !inside(b,r)) return false;
        if (const auto i=channels.find(net); i!=channels.end())
            if (std::min(a.x,b.x)-r<i->second.first ||
                std::max(a.x,b.x)+r>i->second.second) return false;
        const Box box=bounds(a,b,r+GAP);
        return bottom.visit(box,[&](int i) {
            const auto& c=copper[i];
            // A new bridge terminal must have clearance even to same-net pads
            // and existing bridge drills; same-net traces can enter its pad.
            if ((net==c.net && (!terminal || c.track>=0)) ||
                !overlaps(box,c.box)) return true;
            const double rr=r+GAP+c.radius;
            const bool ok=(c.pad ? lineBox(a,b,c.box) : lineLine(a,b,c.a,c.b)) >= rr*rr;
            if (!ok && hits && c.net>0 && c.net!=net && i>=int(pads.size())) ++(*hits)[c.net];
            if (!ok && conflicts && c.track>=0) {
                if (std::find(conflicts->begin(),conflicts->end(),c.track)==conflicts->end())
                    conflicts->push_back(c.track);
                return true;
            }
            return ok;
        });
    }
    bool topClear(Box b) const {
        return upper.visit(b,[&](int i) { return !overlaps(b,top[i]); });
    }
    bool bridgeClear(int net,P a,P b,std::map<int,int>* hits,
                     std::vector<int>* conflicts=nullptr) const {
        if (!inside(a,TERMINAL)||!inside(b,TERMINAL)) return false;
        for (Box e : envelope(a,b)) if (!topClear(e)) return false;
        return clear(net,a,a,LAND,hits,conflicts,true) && clear(net,b,b,LAND,hits,conflicts,true);
    }
    struct Group { std::vector<P> anchors; std::vector<size_t> tracks; bool hasPin=false; };
    std::vector<Group> groups(int net, bool withAnchors) const {
        const auto& ps=pins.at(net);
        std::vector<const Route*> rs;
        std::vector<size_t> indices;
        for (size_t i=0;i<routes.size();++i) if (routes[i].net==net) {
            indices.push_back(i); rs.push_back(&routes[i]);
        }
        const int np=int(ps.size()), nr=int(rs.size());
        Dsu ds(np+nr);
        auto endpoints=[](const Route& r) {
            return std::array<std::pair<P,P>,2>{{{r.a,r.bridge ? r.a : r.b},{r.b,r.b}}};
        };
        // Use pad centres and circular cores for connectivity, not rectangular
        // pad corners that could represent empty space on the actual board.
        const double rad=radius(net);
        for (int i=0;i<np;++i) {
            const auto& p=pads[ps[i]];
            const double core=std::min(p.box.r-p.p.x,p.box.b-p.p.y);
            for (int j=0;j<i;++j) {
                const auto& q=pads[ps[j]];
                if (distance(p.p,q.p) <= core+std::min(q.box.r-q.p.x,q.box.b-q.p.y)-EPS)
                    ds.unite(i,j);
            }
            for (int j=0;j<nr;++j) {
                const auto& r=*rs[j];
                const double touch=core+(r.bridge ? LAND : rad)-EPS;
                for (auto ab:endpoints(r))
                    if (pointLine(p.p,ab.first,ab.second)<=touch*touch) ds.unite(i,np+j);
            }
        }
        for (int i=0;i<nr;++i) for (int j=0;j<i;++j) {
            const Route& a=*rs[i], &b=*rs[j];
            const double touch=(a.bridge ? LAND : rad)+(b.bridge ? LAND : rad)-EPS;
            if (!overlaps(bounds(a.a,a.b,touch),bounds(b.a,b.b))) continue;
            bool linked=false;
            for (auto ab:endpoints(a)) for (auto cd:endpoints(b))
                if (lineLine(ab.first,ab.second,cd.first,cd.second)<=touch*touch) linked=true;
            if (linked) ds.unite(np+i,np+j);
        }
        std::map<int,int> ids;
        std::vector<Group> out;
        auto group=[&](int i) -> Group& {
            auto [it,inserted]=ids.emplace(ds.root(i),int(out.size()));
            if (inserted) out.emplace_back();
            return out[it->second];
        };
        // Keep orphaned draft copper in the count too: KiCad can report it as
        // unconnected even when all schematic pins are already joined.
        for (int i=0;i<np;++i) {
            auto& g=group(i);
            g.hasPin=true;
            if (withAnchors) {
                const Pad& pad=pads[ps[i]];
                g.anchors.push_back(pad.p);
                const double core=std::min(pad.box.r-pad.p.x,pad.box.b-pad.p.y);
                for (P d : {P{.65,0},P{-.65,0},P{0,.65},P{0,-.65}})
                    g.anchors.push_back(interpolate(pad.p,pad.p+d*core,1));
            }
        }
        for (int j=0;j<nr;++j) {
            auto& g=group(np+j);
            g.tracks.push_back(indices[j]);
            if (!withAnchors) continue;
            const Route& r=*rs[j];
            g.anchors.push_back(r.a);
            g.anchors.push_back(r.b);
            if (!r.bridge) {
                const int n=std::min(400,int(std::ceil(distance(r.a,r.b)/.75)));
                for (int k=1;k<n;++k) g.anchors.push_back(interpolate(r.a,r.b,double(k)/n));
            }
        }
        if (withAnchors) for (auto& g:out) {
            std::sort(g.anchors.begin(),g.anchors.end(),[](P a,P b) {
                return std::tie(a.x,a.y)<std::tie(b.x,b.y);
            });
            g.anchors.erase(std::unique(g.anchors.begin(),g.anchors.end(),[](P a,P b) {
                return distance(a,b)<EPS;
            }),g.anchors.end());
        }
        return out;
    }
    int opens(int net) const { return std::max(0,int(groups(net,false).size())-1); }
    void pruneOrphans(const std::vector<int>& nets) {
        std::vector<bool> remove(routes.size());
        for (int n:nets) for (const auto& g:groups(n,false))
            if (!g.hasPin) for (auto k:g.tracks) remove[k]=true;
        size_t kept=0;
        for (size_t i=0;i<routes.size();++i) if (!remove[i]) routes[kept++]=routes[i];
        routes.resize(kept);
    }
    void pruneStubs(const std::vector<int>& nets) {
        std::vector<bool> remove(routes.size());
        for (int n:nets) {
            std::vector<size_t> tracks;
            for (size_t i=0;i<routes.size();++i)
                if (routes[i].net==n) tracks.push_back(i);
            const double rr=radius(n);
            auto attached=[&](P x,size_t self) {
                for (int p:pins.at(n)) {
                    const auto& pad=pads[p];
                    const double core=std::min(pad.box.r-pad.p.x,pad.box.b-pad.p.y);
                    if (sq(x-pad.p) <= (core+rr-EPS)*(core+rr-EPS)) return true;
                }
                for (size_t j:tracks) if (j!=self && !remove[j]) {
                    const auto& r=routes[j];
                    if (r.bridge) {
                        const double touch=LAND+rr-EPS;
                        if (std::min(sq(x-r.a),sq(x-r.b))<=touch*touch) return true;
                    } else {
                        if (pointLine(x,r.a,r.b)<=(rr+EPS)*(rr+EPS)) return true;
                        // A branch ending just off this centreline may still
                        // land well inside the other track's endpoint cap.
                        if (std::min(sq(x-r.a),sq(x-r.b))<=(2*rr-EPS)*(2*rr-EPS)) return true;
                    }
                }
                return false;
            };
            bool changed;
            do {
                changed=false;
                for (size_t i:tracks) if (!remove[i]) {
                    const auto& r=routes[i];
                    if (!attached(r.a,i)||!attached(r.b,i)) {
                        remove[i]=true;
                        changed=true;
                    }
                }
            } while (changed);
        }
        size_t kept=0;
        for (size_t i=0;i<routes.size();++i) if (!remove[i]) routes[kept++]=routes[i];
        routes.resize(kept);
    }
};

P point(int i) { return {i%NX*GRID,i/NX*GRID}; }
int node(int x,int y) { return y*NX+x; }
struct Cell {
    int epoch=0, g=0, parent=-1;
    int aimEpoch=0;
    P aim{};
    int aimCost=0;
    bool bridge=false;
};
struct Queue {
    int f,g,id;
    bool operator<(const Queue& q) const {
        return std::tuple(f,-g,id)>std::tuple(q.f,-q.g,q.id);
    }
};
struct Search {
    World& w;
    int epoch=0;
    std::vector<Cell> cells=std::vector<Cell>(NX*NY);
    std::map<int,int> hits;
    int budget;
    double bridgePenalty;
    std::vector<int> conflicts;
    int softPenalty=0;
    explicit Search(World& world,int limit,double penalty) : w(world),budget(limit),bridgePenalty(penalty) {}

    std::vector<Route> find(int net, const std::vector<P>& a,const std::vector<P>& b,
                            P nearA,P nearB,double margin,int cap,bool bridges) {
        ++epoch;
        Box region=bounds(nearA,nearB,margin);
        double rad=w.radius(net);
        std::vector<int> crossing;
        auto stepCost=[&](P a,P b,double r) {
            crossing.clear();
            if (!w.clear(net,a,b,r,softPenalty ? nullptr : &hits,softPenalty ? &crossing : nullptr))
                return -1;
            return int(crossing.size())*softPenalty;
        };
        std::priority_queue<Queue> q;
        Box goals{INF,INF,-INF,-INF};
        auto snaps=[&](P x,auto callback) {
            if (!overlaps(bounds(x,x),region)) return;
            int gx=int(std::lround(x.x/GRID)),gy=int(std::lround(x.y/GRID));
            for (int j=std::max(0,gy-2);j<=std::min(NY-1,gy+2);++j)
                for (int i=std::max(0,gx-2);i<=std::min(NX-1,gx+2);++i) {
                    int k=node(i,j);
                    P p=point(k);
                    if (!overlaps(bounds(p,p),region)) continue;
                    int penalty=stepCost(p,x,rad);
                    if (penalty>=0) callback(k,x,int(std::lround(1000*distance(p,x)))+penalty);
                }
        };
        for (P p:b) snaps(p,[&](int id,P anchor,int cost) {
            auto& c=cells[id];
            if (c.aimEpoch!=epoch || c.aimCost>cost) {
                c.aimEpoch=epoch; c.aim=anchor; c.aimCost=cost;
                goals=join(goals,bounds(point(id),point(id)));
            }
        });
        if (goals.l==INF) return {};
        auto push=[&](int id,int g,int parent,bool br,P start) {
            auto& c=cells[id];
            if (c.epoch==epoch && g>=c.g) return;
            c.epoch=epoch; c.g=g; c.parent=parent; c.bridge=br;
            if (parent<0) startPoints[id]=start;
            P p=point(id);
            double dx=std::max({0.,goals.l-p.x,p.x-goals.r});
            double dy=std::max({0.,goals.t-p.y,p.y-goals.b});
            const int h=int(1080*(std::max(dx,dy)+.41421356*std::min(dx,dy)));
            q.push({g+h,g,id});
        };
        startPoints.clear();
        for (P p:a) snaps(p,[&](int id,P anchor,int cost) { push(id,cost,-1,false,anchor); });
        static constexpr int dx[]={1,1,0,-1,-1,-1,0,1};
        static constexpr int dy[]={0,1,1,1,0,-1,-1,-1};
        int best=-1,bestCost=std::numeric_limits<int>::max();
        while (!q.empty() && cap>0) {
            auto [f,g,id]=q.top(); q.pop();
            if (f>=bestCost) break;
            const auto& c=cells[id];
            if (c.g!=g) continue;
            --cap;
            if (c.aimEpoch==epoch && g+c.aimCost<bestCost) {
                best=id; bestCost=g+c.aimCost;
            }
            P p=point(id);
            int x=id%NX,y=id/NX;
            for (int d=0;d<8;++d) {
                const int ix=x+dx[d],iy=y+dy[d];
                if (ix<0||ix>=NX||iy<0||iy>=NY) continue;
                const int k=node(ix,iy),cost=g+(d%2 ? 354 : 250);
                if (cells[k].epoch==epoch && cells[k].g<=cost) continue;
                P next=point(k);
                if (!overlaps(bounds(next,next),region)) continue;
                int penalty=stepCost(p,next,rad);
                if (penalty>=0) push(k,cost+penalty,id,false,{});
            }
            if (!bridges||!inside(p,TERMINAL)||!w.topClear(bounds(p,p,TERMINAL))) continue;
            for (int sign : {-1,1}) {
                const P probe{p.x,p.y+sign*2.0};
                if (w.clear(net,p,probe,rad,nullptr)) continue;
                for (int step=11;step<=60;++step) {
                    const int iy=y+step*sign;
                    if (iy<0||iy>=NY) break;
                    const int k=node(x,iy);
                    P next=point(k);
                    if (!overlaps(bounds(next,next),region) ||
                        !w.topClear(bounds(p,next,WIRE))) break;
                    const int cost=g+int(1000*bridgePenalty)+step*250;
                    if (cells[k].epoch==epoch && cells[k].g<=cost) continue;
                    crossing.clear();
                    if (w.bridgeClear(net,p,next,softPenalty ? nullptr : &hits,
                                      softPenalty ? &crossing : nullptr))
                        push(k,cost+int(crossing.size())*softPenalty*4,id,true,{});
                }
            }
        }
        if (best<0) return {};
        std::vector<Route> path;
        auto add=[&](P a,P b,bool link) {
            if (distance(a,b)<EPS) return;
            if (link && a.y>b.y) std::swap(a,b);
            path.push_back({net,a,b,link});
        };
        add(cells[best].aim,point(best),false);
        for (int i=best;;) {
            auto& c=cells[i];
            if (c.parent<0) {
                add(point(i),startPoints.at(i),false);
                break;
            }
            add(point(i),point(c.parent),c.bridge);
            i=c.parent;
        }
        std::vector<Route> compact;
        for (const auto& r:path) {
            if (!compact.empty() && !r.bridge && !compact.back().bridge) {
                auto& last=compact.back();
                if (distance(last.b,r.a)<EPS && std::abs(cross(last.b-last.a,r.b-r.a))<EPS &&
                    dot(last.b-last.a,r.b-r.a)>0)
                    { last.b=r.b; continue; }
            }
            compact.push_back(r);
        }
        for (size_t i=0;i<compact.size();++i) if (compact[i].bridge)
            for (size_t j=0;j<i;++j)
                if (compact[j].bridge && bridgesOverlap(compact[i],compact[j])) return {};
        conflicts.clear();
        if (softPenalty) {
            for (const auto& r:compact) {
                const bool valid=r.bridge ? w.bridgeClear(net,r.a,r.b,nullptr,&conflicts)
                    : w.clear(net,r.a,r.b,rad,nullptr,&conflicts);
                if (!valid) return {};
            }
            std::sort(conflicts.begin(),conflicts.end());
        }
        return compact;
    }

    std::map<int,P> startPoints;
    std::vector<Route> connect(int net,int effort) {
        auto groups=w.groups(net,true);
        struct Pair { double d; size_t i,j; P a,b; };
        std::vector<Pair> pairs;
        for (size_t i=0;i<groups.size();++i) for (size_t j=0;j<i;++j) {
            Pair p{INF,i,j,{},{}};
            for (P a:groups[i].anchors) for (P b:groups[j].anchors) {
                double d=sq(a-b);
                if (d<p.d) { p.d=d; p.a=a; p.b=b; }
            }
            pairs.push_back(p);
        }
        std::stable_sort(pairs.begin(),pairs.end(),[](const Pair& a,const Pair& b){return a.d<b.d;});
        for (size_t i=0;i<pairs.size() && i<size_t(effort>0 ? 8 : 4);++i) {
            const auto& p=pairs[i];
            if (!std::isfinite(p.d) || p.d>=INF) continue;
            const auto& a=groups[p.i].anchors;
            const auto& b=groups[p.j].anchors;
            if (!softPenalty && w.clear(net,p.a,p.b,w.radius(net),&hits)) {
                conflicts.clear();
                return {{net,p.a,p.b,false}};
            }
            for (double m : {6.,17.,40.,90.}) {
                if (effort==0 && m>17) break;
                if (effort==1 && m>40) break;
                if (i>=2 && m>17) break;
                auto path=find(net,a,b,p.a,p.b,m,int(budget*(m<=6 ? .35 : 1)),true);
                if (!path.empty()) return path;
            }
        }
        return {};
    }
};

void emit(std::ostream& out,const std::vector<Route>& state) {
    out<<std::fixed<<std::setprecision(6);
    for (const auto& r:state)
        out<<(r.bridge?"bridge ":"segment ")<<r.net<<' '<<r.a.x<<' '<<r.a.y<<' '
           <<r.b.x<<' '<<r.b.y<<'\n';
}
void checkpoint(const std::string& path,const std::vector<Route>& state) {
    if (path.empty()) return;
    const auto temp=path+".part";
    {
        std::ofstream out(temp);
        emit(out,state);
        out.close();
        if (!out) throw std::runtime_error("cannot write checkpoint: "+temp);
    }
    if (std::rename(temp.c_str(),path.c_str())!=0)
        throw std::runtime_error("cannot replace checkpoint: "+path);
}
void load(World& w) {
    std::string line;
    int lineno=0;
    while (std::getline(std::cin,line)) {
        ++lineno;
        line.resize(std::min(line.size(),line.find('#')));
        std::istringstream in(line);
        std::string kind;
        if (!(in>>kind)) continue;
        const auto bad=[&]() { throw std::runtime_error("invalid input line "+std::to_string(lineno)); };
        const auto valid=[](P a) { return std::isfinite(a.x)&&std::isfinite(a.y); };
        const auto onBoard=[](P a) { return a.x>=0&&a.x<=W&&a.y>=0&&a.y<=H; };
        if (kind=="pad") {
            int net; P p,d;
            if (!(in>>net>>p.x>>p.y>>d.x>>d.y) || net<0 || !onBoard(p) || !valid(d) ||
                d.x<0 || d.y<0 || d.x>W || d.y>H) bad();
            if (net>0) w.pins[net].push_back(int(w.pads.size()));
            w.pads.push_back({net,p,{p.x-d.x,p.y-d.y,p.x+d.x,p.y+d.y}});
        } else if (kind=="block") {
            P a,b;
            if (!(in>>a.x>>a.y>>b.x>>b.y) || !valid(a) || !valid(b)) bad();
            w.blocks.push_back(bounds(a,b));
        } else if (kind=="channel") {
            int net; double left,right;
            if (!(in>>net>>left>>right) || net<=0 || !std::isfinite(left) ||
                !std::isfinite(right) || left<0 || right>W || left>=right) bad();
            w.channels[net]={left,right};
        } else if (kind=="width") {
            int net; double width;
            if (!(in>>net>>width) || net<=0 || !std::isfinite(width) || width<=0 || width>=W) bad();
            w.widths[net]=width;
        } else if (kind=="segment" || kind=="bridge") {
            Route r{};
            r.bridge=kind=="bridge";
            if (!(in>>r.net>>r.a.x>>r.a.y>>r.b.x>>r.b.y) || r.net<=0 ||
                !onBoard(r.a) || !onBoard(r.b) || distance(r.a,r.b)<EPS) bad();
            if (r.bridge) {
                if (r.a.y>r.b.y) std::swap(r.a,r.b);
                if (std::abs(r.a.x-r.b.x)>EPS || r.b.y-r.a.y<2.54-EPS ||
                    r.b.y-r.a.y>15.24+EPS) bad();
            }
            w.routes.push_back(r);
            w.pins.try_emplace(r.net);
        } else bad();
        std::string extra;
        if (in>>extra) bad();
    }
}
}  // namespace

int main(int argc,char** argv) {
    try {
        std::locale::global(std::locale::classic());
        int passes=3,budget=18000,seed=1,attempts=4,escape=0;
        double penalty=6.;
        std::string save,order="mixed";
        bool fresh=false,cleanInput=false;
        for (int i=1;i<argc;++i) {
            std::string arg=argv[i];
            auto value=[&]() -> std::string {
                if (++i>=argc) throw std::runtime_error("missing value for "+arg);
                return argv[i];
            };
            if (arg=="--passes") passes=std::stoi(value());
            else if (arg=="--budget") budget=std::stoi(value());
            else if (arg=="--seed") seed=std::stoi(value());
            else if (arg=="--attempts") attempts=std::stoi(value());
            else if (arg=="--escape") escape=std::stoi(value());
            else if (arg=="--order") order=value();
            else if (arg=="--prune-stubs") cleanInput=true;
            else if (arg=="--bridge-penalty") penalty=std::stod(value());
            else if (arg=="--checkpoint") save=value();
            else if (arg=="--fresh") fresh=true;
            else if (arg=="--help") {
                std::cout<<"route [--passes N] [--budget N] [--seed N] [--bridge-penalty MM]\n"
                            "      [--order mixed|long|short|random] [--attempts N] [--escape N]\n"
                            "      [--checkpoint PATH] [--fresh] [--prune-stubs] < draft.txt > candidate.txt\n";
                return 0;
            } else throw std::runtime_error("unknown option: "+arg);
        }
        if (passes<0||budget<100||attempts<0||attempts>32||escape<0||
            !std::isfinite(penalty)||penalty<0||penalty>10000)
            throw std::runtime_error("invalid search limits");
        if (order!="mixed"&&order!="long"&&order!="short"&&order!="random")
            throw std::runtime_error("invalid net ordering");
        World w;
        load(w);
        if (fresh) w.routes.clear();
        std::map<int,double> span;
        std::vector<int> allNets;
        for (const auto& [n,ps]:w.pins) {
            allNets.push_back(n);
            if (ps.empty()) continue;
            Box box=w.pads[ps.front()].box;
            for (int p:ps) box=join(box,w.pads[p].box);
            span[n]=std::hypot(box.r-box.l,box.b-box.t);
        }
        if (cleanInput) w.pruneStubs(allNets);
        std::map<int,int> open;
        auto score=[&]() {
            int total=0;
            for (auto& [n,p] : w.pins) total+=(open[n]=w.opens(n));
            return total;
        };
        auto best=w.routes;
        int bestScore=score();
        std::cerr<<"initial opens "<<bestScore<<'\n';
        checkpoint(save,best);
        Search search(w,budget,penalty);
        std::mt19937 rng(seed);
        w.index();
        auto routeNet=[&](int net,int limit,int effort) {
            for (int j=0;j<limit;++j) {
                int before=w.opens(net);
                if (!before) break;
                size_t size=w.routes.size();
                const auto path=search.connect(net,effort);
                if (path.empty()) break;
                w.routes.insert(w.routes.end(),path.begin(),path.end());
                if (w.opens(net)>=before) { w.routes.resize(size); break; }
                w.index();
            }
        };
        auto remember=[&](int total,int net) {
            if (total>=bestScore) return;
            bestScore=total; best=w.routes;
            checkpoint(save,best);
            std::cerr<<"best opens "<<bestScore<<" after net "<<net
                     <<" ("<<best.size()<<" records)\n";
        };
        for (int pass=0;pass<passes && bestScore>0;++pass) {
            std::vector<int> nets;
            for (const auto& [n,k]:open) if (k>0) nets.push_back(n);
            if (pass || order=="random") std::shuffle(nets.begin(),nets.end(),rng);
            if (order!="random") std::stable_sort(nets.begin(),nets.end(),[&](int a,int b) {
                if (order=="long") return span[a]>span[b];
                if (order=="short") return span[a]<span[b];
                return pass%2==0 ? open[a]<open[b] : open[a]>open[b];
            });
            int sideways=escape;
            std::cerr<<"pass "<<pass+1<<" ("<<nets.size()<<" open nets)\n";
            for (int n:nets) {
                if (!open[n]) continue;
                int before=open[n];
                search.hits.clear();
                routeNet(n,before,pass==0 ? 0 : (pass==1 ? 1 : 2));
                open[n]=w.opens(n);
                int total=std::accumulate(open.begin(),open.end(),0,[](int s,const auto& e){return s+e.second;});
                remember(total,n);
                if (!open[n] || pass==0) continue;
                const auto clean=w.routes;
                const auto initialHits=search.hits;
                bool negotiated=false;
                const std::array<int,8> prices{{1700,4400,850,2800,6000,550,11000,350}};
                for (int attempt=0;attempt<attempts;++attempt) {
                    const int price=prices[(attempt+std::max(0,pass-2))%prices.size()];
                    search.softPenalty=price;
                    auto path=search.connect(n,0);
                    search.softPenalty=0;
                    if (path.empty() || search.conflicts.empty() || search.conflicts.size()>14) continue;
                    std::vector<int> affected;
                    for (int k:search.conflicts) affected.push_back(w.routes[k].net);
                    std::sort(affected.begin(),affected.end());
                    affected.erase(std::unique(affected.begin(),affected.end()),affected.end());
                    if (affected.size()>4) continue;
                    for (auto i=search.conflicts.rbegin();i!=search.conflicts.rend();++i)
                        w.routes.erase(w.routes.begin()+*i);
                    w.routes.insert(w.routes.end(),path.begin(),path.end());
                    w.pruneOrphans(affected);
                    w.pruneStubs(affected);
                    w.index();
                    std::vector<int> repair=affected;
                    std::stable_sort(repair.begin(),repair.end(),[&](int a,int b) {
                        return w.opens(a)<w.opens(b);
                    });
                    for (int blocker:repair)
                        routeNet(blocker,std::max(0,w.opens(blocker)-open[blocker]),0);
                    w.pruneStubs(affected);
                    int trial=total-open[n]+w.opens(n);
                    for (int blocker:affected) trial+=w.opens(blocker)-open[blocker];
                    if (trial<total || (trial==total && sideways>0 && w.opens(n)<open[n])) {
                        if (trial==total) --sideways;
                        open[n]=w.opens(n);
                        for (int blocker:affected) open[blocker]=w.opens(blocker);
                        remember(trial,n);
                        w.index();
                        negotiated=true;
                        break;
                    }
                    w.routes=clean;
                    w.index();
                }
                if (negotiated) continue;
                std::vector<std::pair<int,int>> hot;
                for (auto [blocked,count]:initialHits)
                    hot.emplace_back(count,blocked);
                std::sort(hot.rbegin(),hot.rend());
                int wholeNetAttempts=0;
                for (auto [count,blocked]:hot) {
                    (void)count;
                    const auto lines=std::count_if(clean.begin(),clean.end(),
                                                   [&](const Route& r){return r.net==blocked;});
                    if (!lines || lines>35) continue;
                    if (++wholeNetAttempts>attempts) break;
                    w.routes=clean;
                    w.routes.erase(std::remove_if(w.routes.begin(),w.routes.end(),
                        [&](const Route& r){return r.net==blocked;}),w.routes.end());
                    w.index();
                    search.hits.clear();
                    routeNet(n,1,0);
                    if (w.opens(n)<open[n]) {
                        routeNet(blocked,w.opens(blocked),0);
                        int trial=total-open[n]-open[blocked]+w.opens(n)+w.opens(blocked);
                        if (trial<total) {
                            open[n]=w.opens(n); open[blocked]=w.opens(blocked);
                            remember(trial,n);
                            break;
                        }
                    }
                    w.routes=clean;
                    w.index();
                }
            }
        }
        std::cerr<<"final opens "<<bestScore<<'\n';
        emit(std::cout,best);
        if (!std::cout) throw std::runtime_error("cannot write route records");
        return 0;
    } catch (const std::exception& e) {
        std::cerr<<"route: "<<e.what()<<'\n';
        return 1;
    }
}
