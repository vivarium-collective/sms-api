(ns gateway
  (:require
   [org.httpkit.server :as hk-server]))

(def channels (atom #{}))

(defn on-open    [ch]             (swap! channels conj ch))
(defn on-close   [ch status-code] (swap! channels disj ch))
(defn on-receive [ch message]
  (doseq [ch @channels]
    (hk-server/send! ch (str "Broadcasting: " message))))

(defn app [ring-req]
  (if-not (:websocket? ring-req)
    {:status 200 :headers {"content-type" "text/html"} :body "Connect WebSockets to this URL."}
    (hk-server/as-channel ring-req
                          {:on-open    on-open
                           :on-receive on-receive
                           :on-close   on-close})))

(def server (hk-server/run-server app {:port 8080}))